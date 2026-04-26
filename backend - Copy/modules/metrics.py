"""
Metrics Module
Collects and compares metrics between standard and advanced RAG
"""

from typing import Dict, List, Tuple
from datetime import datetime
import json


class MetricsCollector:
    """Collects metrics for both RAG modes"""
    
    def __init__(self):
        self.standard_metrics = []
        self.advanced_metrics = []
    
    def record_standard_rag(self, metrics: Dict) -> None:
        """Record standard RAG metrics"""
        metrics["timestamp"] = datetime.now().isoformat()
        self.standard_metrics.append(metrics)
    
    def record_advanced_rag(self, metrics: Dict) -> None:
        """Record advanced RAG metrics"""
        metrics["timestamp"] = datetime.now().isoformat()
        self.advanced_metrics.append(metrics)
    
    def get_statistics(self, metrics_list: List[Dict]) -> Dict:
        """Calculate statistics from metrics"""
        if not metrics_list:
            return {}
        
        latencies = [m.get("latency_ms", 0) for m in metrics_list]
        retrieval_counts = [m.get("num_retrieved", 0) for m in metrics_list]
        cosine_scores = [s for m in metrics_list for s in m.get("retrieval_scores", [])]
        
        def safe_avg(values):
            return sum(values) / len(values) if values else 0
        
        def safe_min(values):
            return min(values) if values else 0
        
        def safe_max(values):
            return max(values) if values else 0
        
        return {
            "num_queries": len(metrics_list),
            "avg_latency_ms": safe_avg(latencies),
            "min_latency_ms": safe_min(latencies),
            "max_latency_ms": safe_max(latencies),
            "avg_retrieval_count": safe_avg(retrieval_counts),
            "avg_cosine_score": safe_avg(cosine_scores),
            "max_cosine_score": safe_max(cosine_scores),
            "min_cosine_score": safe_min(cosine_scores),
        }
    
    def get_standard_stats(self) -> Dict:
        """Get statistics for standard RAG"""
        return self.get_statistics(self.standard_metrics)
    
    def get_advanced_stats(self) -> Dict:
        """Get statistics for advanced RAG"""
        return self.get_statistics(self.advanced_metrics)
    
    def compare_modes(self) -> Dict:
        """Compare metrics between both modes"""
        standard_stats = self.get_standard_stats()
        advanced_stats = self.get_advanced_stats()
        
        if not standard_stats or not advanced_stats:
            return {"error": "Not enough data for comparison"}
        
        comparison = {
            "standard_rag": standard_stats,
            "advanced_rag": advanced_stats,
            "comparison": {
                "latency_improvement": (
                    (standard_stats.get("avg_latency_ms", 0) - advanced_stats.get("avg_latency_ms", 0)) /
                    standard_stats.get("avg_latency_ms", 1) * 100
                ),
                "score_improvement": (
                    advanced_stats.get("avg_cosine_score", 0) - standard_stats.get("avg_cosine_score", 0)
                ),
            }
        }
        
        return comparison


class RAGBenchmark:
    """Comprehensive benchmarking for RAG systems"""
    
    def __init__(self):
        self.results = {
            "standard_rag": [],
            "advanced_rag": []
        }
    
    def add_result(self, mode: str, query: str, retrieved_docs: List[Dict],
                  retrieval_scores: List[float], latency_ms: float,
                  additional_metrics: Dict = None) -> None:
        """
        Add a benchmark result
        
        Args:
            mode: "standard_rag" or "advanced_rag"
            query: Query string
            retrieved_docs: List of retrieved documents
            retrieval_scores: List of retrieval scores
            latency_ms: Latency in milliseconds
            additional_metrics: Additional metric dict
        """
        result = {
            "query": query,
            "num_docs": len(retrieved_docs),
            "avg_score": sum(retrieval_scores) / len(retrieval_scores) if retrieval_scores else 0,
            "max_score": max(retrieval_scores) if retrieval_scores else 0,
            "min_score": min(retrieval_scores) if retrieval_scores else 0,
            "latency_ms": latency_ms,
            "content_length": sum(len(d.get("content", "").split()) for d in retrieved_docs),
            "timestamp": datetime.now().isoformat(),
            **(additional_metrics or {})
        }
        
        self.results[mode].append(result)
    
    def get_summary(self) -> Dict:
        """Get summary statistics"""
        def calc_stats(results):
            if not results:
                return {}
            
            latencies = [r["latency_ms"] for r in results]
            scores = [r["avg_score"] for r in results]
            doc_counts = [r["num_docs"] for r in results]
            
            return {
                "num_queries": len(results),
                "avg_latency_ms": sum(latencies) / len(latencies),
                "avg_score": sum(scores) / len(scores),
                "avg_docs_retrieved": sum(doc_counts) / len(doc_counts),
            }
        
        standard_stats = calc_stats(self.results["standard_rag"])
        advanced_stats = calc_stats(self.results["advanced_rag"])
        
        return {
            "standard_rag": standard_stats,
            "advanced_rag": advanced_stats,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_detailed_comparison(self) -> Dict:
        """Get detailed comparison between modes"""
        summary = self.get_summary()
        
        standard = summary.get("standard_rag", {})
        advanced = summary.get("advanced_rag", {})
        
        comparison = {}
        
        if standard and advanced:
            latency_diff = standard.get("avg_latency_ms", 0) - advanced.get("avg_latency_ms", 0)
            score_diff = advanced.get("avg_score", 0) - standard.get("avg_score", 0)
            
            comparison = {
                "latency_difference_ms": latency_diff,
                "latency_improvement_pct": (latency_diff / standard.get("avg_latency_ms", 1)) * 100,
                "score_improvement": score_diff,
                "score_improvement_pct": (score_diff / standard.get("avg_score", 1)) * 100 if standard.get("avg_score") else 0,
            }
        
        return {
            "summary": summary,
            "comparison": comparison,
            "standard_rag_details": self.results["standard_rag"],
            "advanced_rag_details": self.results["advanced_rag"],
        }
    
    def export_csv(self, filepath: str, mode: str = None) -> None:
        """Export results to CSV"""
        import csv
        
        modes = [mode] if mode else ["standard_rag", "advanced_rag"]
        
        for m in modes:
            if not self.results[m]:
                continue
            
            csv_path = filepath.replace(".csv", f"_{m}.csv")
            
            with open(csv_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.results[m][0].keys())
                writer.writeheader()
                writer.writerows(self.results[m])
            
            print(f"Exported {m} results to {csv_path}")


class AdvancedRAGMetrics:
    """Metrics specific to advanced RAG"""
    
    @staticmethod
    def extract_advanced_metrics(graph_result: Dict, reranking_result: Dict,
                                 optimization_stats: Dict) -> Dict:
        """
        Extract comprehensive metrics from advanced RAG components
        
        Args:
            graph_result: Semantic graph retrieval result
            reranking_result: Reranking result
            optimization_stats: Context optimization stats
            
        Returns:
            Comprehensive metrics dict
        """
        return {
            "graph_nodes_explored": graph_result.get("num_nodes", 0),
            "graph_hops": graph_result.get("num_hops", 0),
            "reranking_strategy": reranking_result.get("strategies", []),
            "reranking_score": reranking_result.get("reranking_scores", []),
            "context_docs_original": optimization_stats.get("original_docs", 0),
            "context_docs_optimized": optimization_stats.get("optimized_docs", 0),
            "token_reduction_pct": optimization_stats.get("token_reduction", 0) * 100,
            "compression_ratio": optimization_stats.get("compression_ratio", 1.0),
        }


if __name__ == "__main__":
    collector = MetricsCollector()
    benchmark = RAGBenchmark()
    print("Metrics modules initialized")
