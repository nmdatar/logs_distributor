from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class LogMessage(BaseModel):
    timestamp: str  # ISO8601 or similar
    level: str      # Simple string, no enum validation needed
    message: str

class LogPacket(BaseModel):
    source: str
    messages: List[LogMessage]

class AnalyzerStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"

class Analyzer(BaseModel):
    id: str
    name: str
    endpoint: str
    weight: float  # Relative weight (0.0 to 1.0)
    status: AnalyzerStatus = AnalyzerStatus.ONLINE
    health_check_url: Optional[str] = None
    last_health_check: Optional[str] = None
    total_messages_processed: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class AnalyzerConfig(BaseModel):
    analyzers: List[Analyzer]
    total_weight: float = 0.0
    
    def add_analyzer(self, analyzer: Analyzer):
        """Add analyzer and recalculate total weight"""
        self.analyzers.append(analyzer)
        self._recalculate_weights()
    
    def remove_analyzer(self, analyzer_id: str):
        """Remove analyzer and recalculate total weight"""
        self.analyzers = [a for a in self.analyzers if a.id != analyzer_id]
        self._recalculate_weights()
    
    def get_online_analyzers(self) -> List[Analyzer]:
        """Get only online analyzers"""
        return [a for a in self.analyzers if a.status == AnalyzerStatus.ONLINE]
    
    def _recalculate_weights(self):
        """Recalculate total weight from online analyzers"""
        online_analyzers = self.get_online_analyzers()
        if online_analyzers:
            total_weight = sum(a.weight for a in online_analyzers)
            # Normalize weights to sum to 1.0
            for analyzer in online_analyzers:
                analyzer.weight = analyzer.weight / total_weight
            self.total_weight = 1.0
        else:
            self.total_weight = 0.0


