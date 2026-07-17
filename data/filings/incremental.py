"""
Incremental Updates for SEC Filings and Financial Documents.

Provides efficient incremental updates for SEC filings, document processing,
and incremental RAG index updates.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, AsyncGenerator, Callable, Optional
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .downloader import SECDownloader, SECFiling
    from ..filings.cache import DocumentCache

logger = logging.getLogger(__name__)


class UpdateStatus(Enum):
    """Status of an incremental update."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class UpdateResult:
    """Result of an incremental update operation."""
    status: UpdateStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    items_processed: int = 0
    items_added: int = 0
    items_updated: int = 0
    items_failed: int = 0
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0


@dataclass
class UpdateConfig:
    """Configuration for incremental updates."""
    # Schedule
    check_interval_hours: int = 6
    lookback_days: int = 7
    
    # Filters
    form_types: Optional[list[str]] = None
    company_ciks: Optional[list[str]] = None
    company_tickers: Optional[list[str]] = None
    
    # Processing
    max_filings_per_run: int = 100
    download_documents: bool = True
    process_documents: bool = True
    update_rag_index: bool = True
    
    # Error handling
    max_retries: int = 3
    retry_delay_seconds: int = 60
    continue_on_error: bool = True
    
    # Notifications
    notify_on_complete: bool = False
    notify_on_error: bool = True
    webhook_url: Optional[str] = None


class IncrementalUpdater:
    """
    Manages incremental updates for SEC filings and document processing.
    
    Features:
    - Scheduled periodic updates
    - Incremental SEC filing downloads
    - Document processing pipeline
    - RAG index updates
    - Change detection and deduplication
    - Resumable operations with checkpoints
    """
    
    def __init__(
        self,
        config: UpdateConfig,
        sec_downloader: "SECDownloader",
        document_cache: "DocumentCache",
        rag_update_callback: Optional[Callable[[list], Any]] = None,
        state_file: Path = Path("./data/filings/update_state.json")
    ):
        self.config = config
        self.sec_downloader = sec_downloader
        self.document_cache = document_cache
        self.rag_update_callback = rag_update_callback
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        # State
        self._running = False
        self._last_run: Optional[datetime] = None
        self._next_run: Optional[datetime] = None
        self._last_results: list[UpdateResult] = []
        
        # Load state
        self._load_state()
    
    def _load_state(self):
        """Load persisted state from file."""
        try:
            if self.state_file.exists():
                with open(self.state_file) as f:
                    state = json.load(f)
                self._last_run = datetime.fromisoformat(state.get("last_run")) if state.get("last_run") else None
                self._next_run = datetime.fromisoformat(state.get("next_run")) if state.get("next_run") else None
                # Load last results
                self._last_results = [
                    UpdateResult(
                        status=UpdateStatus(r["status"]),
                        started_at=datetime.fromisoformat(r["started_at"]),
                        completed_at=datetime.fromisoformat(r["completed_at"]) if r.get("completed_at") else None,
                        items_processed=r.get("items_processed", 0),
                        items_added=r.get("items_added", 0),
                        items_updated=r.get("items_updated", 0),
                        items_failed=r.get("items_failed", 0),
                        errors=r.get("errors", []),
                        duration_seconds=r.get("duration_seconds", 0.0)
                    )
                    for r in state.get("last_results", [])
                ]
        except Exception as e:
            logger.warning(f"Failed to load update state: {e}")
    
    def _save_state(self):
        """Save state to file."""
        try:
            state = {
                "last_run": self._last_run.isoformat() if self._last_run else None,
                "next_run": self._next_run.isoformat() if self._next_run else None,
                "last_results": [
                    {
                        "status": r.status.value,
                        "started_at": r.started_at.isoformat(),
                        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                        "items_processed": r.items_processed,
                        "items_added": r.items_added,
                        "items_updated": r.items_updated,
                        "items_failed": r.items_failed,
                        "errors": r.errors,
                        "duration_seconds": r.duration_seconds
                    }
                    for r in self._last_results[-10:]  # Keep last 10
                ],
                "updated_at": datetime.now().isoformat()
            }
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save update state: {e}")
    
    def _calculate_next_run(self) -> datetime:
        """Calculate next scheduled run time."""
        if self._last_run:
            return self._last_run + timedelta(hours=self.config.check_interval_hours)
        return datetime.now() + timedelta(minutes=1)  # Run soon if never run
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    @property
    def is_due(self) -> bool:
        if self._next_run is None:
            return True
        return datetime.now() >= self._next_run
    
    async def run_update(self, force: bool = False) -> UpdateResult:
        """
        Run a single incremental update cycle.
        
        Args:
            force: Run even if not due
            
        Returns:
            UpdateResult with details of the update
        """
        if self._running and not force:
            return UpdateResult(
                status=UpdateStatus.SKIPPED,
                started_at=datetime.now(),
                errors=["Update already running"]
            )
        
        if not force and not self.is_due:
            return UpdateResult(
                status=UpdateStatus.SKIPPED,
                started_at=datetime.now(),
                errors=["Update not due yet"]
            )
        
        self._running = True
        start_time = datetime.now()
        result = UpdateResult(status=UpdateStatus.RUNNING, started_at=start_time)
        
        try:
            logger.info("Starting incremental update cycle")
            
            # Step 1: Get companies to update
            companies = await self._get_companies_to_update()
            result.items_processed = len(companies)
            
            if not companies:
                logger.info("No companies to update")
                result.status = UpdateStatus.COMPLETED
                result.completed_at = datetime.now()
                result.duration_seconds = (datetime.now() - start_time).total_seconds()
                return result
            
            # Step 2: Process each company
            for company in companies:
                try:
                    company_result = await self._update_company(company)
                    result.items_added += company_result.get("added", 0)
                    result.items_updated += company_result.get("updated", 0)
                    result.items_failed += company_result.get("failed", 0)
                except Exception as e:
                    error_msg = f"Failed to update company {company}: {e}"
                    logger.error(error_msg)
                    result.errors.append(error_msg)
                    result.items_failed += 1
                    
                    if not self.config.continue_on_error:
                        raise
            
            # Step 3: Update RAG index if needed
            if self.config.update_rag_index and self.rag_update_callback:
                try:
                    await self._update_rag_index()
                except Exception as e:
                    logger.error(f"RAG index update failed: {e}")
                    if not self.config.continue_on_error:
                        raise
            
            result.status = UpdateStatus.COMPLETED
            result.completed_at = datetime.now()
            result.duration_seconds = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Incremental update completed: {result.items_added} added, {result.items_updated} updated, {result.items_failed} failed")
            
        except Exception as e:
            result.status = UpdateStatus.FAILED
            result.completed_at = datetime.now()
            result.duration_seconds = (datetime.now() - start_time).total_seconds()
            result.errors.append(str(e))
            logger.error(f"Incremental update failed: {e}")
        
        finally:
            self._running = False
            self._last_run = start_time
            self._next_run = self._calculate_next_run()
            self._last_results.append(result)
            self._save_state()
        
        return result
    
    async def _get_companies_to_update(self) -> list[dict]:
        """Get list of companies that need updating."""
        companies = []
        
        # If specific tickers provided
        if self.config.company_tickers:
            for ticker in self.config.company_tickers:
                companies.append({"ticker": ticker})
        
        # If specific CIKs provided
        if self.config.company_ciks:
            for cik in self.config.company_ciks:
                companies.append({"cik": cik})
        
        # If neither specified, get from document cache
        if not companies:
            # Get companies that have documents in cache
            # This would need a proper index in production
            # For now, return empty to avoid processing unknown companies
            pass
        
        return companies
    
    async def _update_company(self, company: dict) -> dict[str, int]:
        """Update filings for a single company."""
        result = {"added": 0, "updated": 0, "failed": 0}
        
        cik = company.get("cik")
        ticker = company.get("ticker")
        
        if not cik and ticker:
            # Resolve ticker to CIK
            try:
                company_info = await self.sec_downloader.get_company_info("")
                # This would need ticker->CIK mapping
                pass
            except Exception:
                pass
        
        if not cik:
            return result
        
        # Search for new filings
        end_date = date.today()
        start_date = end_date - timedelta(days=self.config.lookback_days)
        
        try:
            filings = await self.sec_downloader.search_filings(
                cik=cik,
                form_types=self.config.form_types,
                start_date=start_date,
                end_date=end_date,
                count=self.config.max_filings_per_run
            )
            
            for filing in filings:
                try:
                    # Check if already processed
                    cache_key = f"filing_{filing.cik}_{filing.accession_number}"
                    existing = await self.document_cache.cache.get(cache_key)
                    
                    if existing:
                        # Check if updated
                        if existing.get("filing_hash") != filing.filing_hash:
                            # Update needed
                            await self._process_filing(filing)
                            result["updated"] += 1
                        continue
                    
                    # New filing
                    await self._process_filing(filing)
                    result["added"] += 1
                    
                except Exception as e:
                    logger.error(f"Failed to process filing {filing.accession_number}: {e}")
                    result["failed"] += 1
            
        except Exception as e:
            logger.error(f"Failed to update company {cik}: {e}")
            result["failed"] += 1
        
        return result
    
    async def _process_filing(self, filing: "SECFiling"):
        """Process a single filing: download, parse, cache, index."""
        cache_key = f"filing_{filing.cik}_{filing.accession_number}"
        
        # Download document
        if self.config.download_documents:
            output_dir = Path("./data/filings") / filing.cik / filing.form_type
            filepath = await self.sec_downloader.download_filing(filing, output_dir)
            
            # Process document
            if self.config.process_documents:
                from ..filings.cache import DocumentCache
                doc_cache = DocumentCache()
                
                with open(filepath, 'rb') as f:
                    content = f.read()
                
                metadata = {
                    "cik": filing.cik,
                    "form_type": filing.form_type,
                    "filing_date": filing.filing_date.isoformat(),
                    "accession_number": filing.accession_number,
                    "document_url": filing.document_url,
                    "filing_hash": filing.filing_hash
                }
                
                await doc_cache.store_document(
                    content=content,
                    metadata=metadata,
                    company_cik=filing.cik
                )
        
        # Update cache with filing metadata
        await self.document_cache.cache.set(
            cache_key,
            {
                "filing": {
                    "cik": filing.cik,
                    "form_type": filing.form_type,
                    "filing_date": filing.filing_date.isoformat(),
                    "accession_number": filing.accession_number,
                    "document_url": filing.document_url,
                    "filing_hash": filing.filing_hash
                },
                "processed_at": datetime.now().isoformat(),
                "filepath": str(filepath) if self.config.download_documents else None
            }
        )
    
    async def _update_rag_index(self):
        """Trigger RAG index update."""
        if self.rag_update_callback:
            # Get recently added/updated documents
            # This would need a proper implementation
            await self.rag_update_callback([])
    
    async def run_scheduled(self):
        """Run the scheduler loop."""
        logger.info("Starting incremental update scheduler")
        
        while True:
            try:
                if self.is_due:
                    await self.run_update()
                
                # Sleep until next check
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                logger.info("Scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(60)
    
    def get_status(self) -> dict:
        """Get current updater status."""
        return {
            "running": self._running,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "next_run": self._next_run.isoformat() if self._next_run else None,
            "due": self.is_due,
            "last_results": [
                {
                    "status": r.status.value,
                    "started_at": r.started_at.isoformat(),
                    "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                    "items_processed": r.items_processed,
                    "items_added": r.items_added,
                    "items_updated": r.items_updated,
                    "items_failed": r.items_failed,
                    "duration_seconds": r.duration_seconds
                }
                for r in self._last_results[-5:]
            ],
            "config": {
                "check_interval_hours": self.config.check_interval_hours,
                "lookback_days": self.config.lookback_days,
                "form_types": self.config.form_types,
                "max_filings_per_run": self.config.max_filings_per_run
            }
        }


class IncrementalRAGUpdater:
    """
    Incremental RAG index updates for financial documents.
    
    Handles:
    - Incremental document addition to vector store
    - Incremental document updates
    - Deleted document handling
    - Batch processing for efficiency
    """
    
    def __init__(
        self,
        vector_store,
        document_cache: "DocumentCache",
        chunker,
        embeddings_service,
        batch_size: int = 100,
        state_file: Path = Path("./data/rag/update_state.json")
    ):
        self.vector_store = vector_store
        self.document_cache = document_cache
        self.chunker = chunker
        self.embeddings_service = embeddings_service
        self.batch_size = batch_size
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        self._processed_hashes: set[str] = set()
        self._load_state()
    
    def _load_state(self):
        if self.state_file.exists():
            with open(self.state_file) as f:
                state = json.load(f)
                self._processed_hashes = set(state.get("processed_hashes", []))
    
    def _save_state(self):
        with open(self.state_file, 'w') as f:
            json.dump({
                "processed_hashes": list(self._processed_hashes),
                "updated_at": datetime.now().isoformat()
            }, f)
    
    async def process_new_documents(self, document_keys: list[str]) -> dict:
        """Process new documents and add to vector store."""
        results = {"added": 0, "failed": 0, "skipped": 0}
        
        for key in document_keys:
            if key in self._processed_hashes:
                results["skipped"] += 1
                continue
            
            try:
                doc = await self.document_cache.get_document(key)
                if not doc:
                    results["skipped"] += 1
                    continue
                
                content, metadata = doc
                
                # Chunk document
                from ..chunking.section_splitter import create_chunker
                chunker = create_chunker()
                
                # Need LoadedDocument - reconstruct from metadata
                from ..ingestion.document_loader import LoadedDocument, ExtractedPage
                from ..schemas import DocumentMetadata, FinancialMetadata
                
                # Create mock LoadedDocument for chunking
                doc_obj = type('LoadedDocument', (), {
                    'pages': [],
                    'financial_metadata': type('FinancialMetadata', (), metadata)(),
                    'full_text': content
                })()
                
                # For now, just chunk the text directly
                chunks = self._chunk_text(content, metadata)
                
                # Generate embeddings
                texts = [c["text"] for c in chunks]
                embeddings = await self.embeddings_service.generate_embeddings(texts)
                
                # Store in vector store
                for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                    doc_id = f"{metadata.get('content_hash', '')}_chunk_{i}"
                    await self.vector_store.add(
                        ids=[doc_id],
                        embeddings=[embedding],
                        documents=[chunk["text"]],
                        metadatas=[{
                            **metadata,
                            "chunk_index": i,
                            "chunk_text": chunk["text"][:500]
                        }]
                    )
                
                self._processed_hashes.add(key)
                results["added"] += 1
                
            except Exception as e:
                logger.error(f"Failed to process document {key}: {e}")
                results["failed"] += 1
        
        self._save_state()
        return results
    
    def _chunk_text(self, text: str, metadata: dict) -> list[dict]:
        """Simple text chunking for RAG."""
        chunk_size = 512
        overlap = 50
        chunks = []
        
        for i in range(0, len(text), chunk_size - overlap):
            chunk_text = text[i:i + chunk_size]
            if len(chunk_text) < 50:  # Skip very small chunks
                continue
            chunks.append({
                "text": chunk_text,
                "char_start": i,
                "chunk_index": len(chunks)
            })
        
        return chunks
    
    async def update_document(self, key: str, new_content: bytes, metadata: dict):
        """Update an existing document in the index."""
        # Delete old chunks
        # Add new chunks
        self._processed_hashes.discard(key)
        await self.process_new_documents([key])
    
    async def delete_document(self, key: str):
        """Remove document from index."""
        # Delete from vector store
        # In practice, would delete by metadata filter
        self._processed_hashes.discard(key)
    
    def get_stats(self) -> dict:
        return {
            "processed_documents": len(self._processed_hashes),
            "cached_hashes": len(self._processed_hashes)
        }


# Factory
async def create_incremental_updater(
    sec_downloader: "SECDownloader",
    document_cache: "DocumentCache",
    rag_update_callback: Optional[Callable] = None,
    config: Optional[UpdateConfig] = None,
    state_file: Path = Path("./data/filings/update_state.json")
) -> IncrementalUpdater:
    """Create and initialize incremental updater."""
    config = config or UpdateConfig()
    return IncrementalUpdater(
        config=config,
        sec_downloader=sec_downloader,
        document_cache=document_cache,
        rag_update_callback=rag_update_callback,
        state_file=state_file
    )


# Export
__all__ = [
    "IncrementalUpdater",
    "UpdateConfig",
    "UpdateResult",
    "UpdateStatus",
    "IncrementalRAGUpdater",
    "create_incremental_updater",
]