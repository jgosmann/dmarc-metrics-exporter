import json
from pathlib import Path

from pydantic import BaseModel, TypeAdapter

from dmarc_metrics_exporter.dmarc_event import Meta

from .dmarc_metrics import DmarcMetrics, DmarcMetricsCollection, InvalidMeta

_Meta = TypeAdapter(Meta)
_DmarcMetrics = TypeAdapter(DmarcMetrics)
_InvalidMeta = TypeAdapter(InvalidMeta)


class _SerializationModel(BaseModel):
    metrics: list[tuple[Meta, DmarcMetrics]]
    invalid_reports: list[tuple[InvalidMeta, int]] = []


class MetricsPersister:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> DmarcMetricsCollection:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                obj = json.load(f)
                is_old_format = isinstance(obj, list)
                if is_old_format:
                    obj = {"metrics": obj}
                model = _SerializationModel(**obj)
                return DmarcMetricsCollection(
                    metrics={
                        _Meta.validate_python(meta): _DmarcMetrics.validate_python(
                            metrics
                        )
                        for meta, metrics in model.metrics
                    },
                    invalid_reports={
                        _InvalidMeta.validate_python(meta): count
                        for meta, count in model.invalid_reports
                    },
                )
        except FileNotFoundError:
            return DmarcMetricsCollection()

    def save(self, metrics: DmarcMetricsCollection):
        model = _SerializationModel(
            metrics=[tuple(item) for item in metrics.items()],
            invalid_reports=[(k, v) for k, v in metrics.invalid_reports.items()],
        )
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(model.model_dump_json())
