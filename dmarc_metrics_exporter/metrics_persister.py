import json
from pathlib import Path
from typing import Any, List, Tuple

from dataclasses_serialization.json import JSONSerializer

from dmarc_metrics_exporter.dmarc_event import Disposition, Meta

from .dmarc_metrics import DmarcMetrics, DmarcMetricsCollection


# false positive, pylint: disable=no-value-for-parameter
@JSONSerializer.register_serializer(Disposition)
def disposition_serializer(disposition: Disposition) -> str:
    return disposition.value


@JSONSerializer.register_serializer(DmarcMetricsCollection)
def dmarc_metrics_collection_serializer(
    metrics: DmarcMetricsCollection,
) -> List[Tuple[Any, Any]]:
    return JSONSerializer.serialize([list(item) for item in metrics.items()])


@JSONSerializer.register_deserializer(Disposition)
def disposition_deserializer(_cls, obj: str) -> Disposition:
    return Disposition(obj)


@JSONSerializer.register_deserializer(DmarcMetricsCollection)
def dmarc_metrics_collection_deserializer(_cls, obj) -> DmarcMetricsCollection:
    return DmarcMetricsCollection(
        dict(
            (
                JSONSerializer.deserialize(Meta, meta),
                JSONSerializer.deserialize(DmarcMetrics, metrics),
            )
            for meta, metrics in obj
        )
    )


class MetricsPersister:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> DmarcMetricsCollection:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return JSONSerializer.deserialize(DmarcMetricsCollection, json.load(f))
        except FileNotFoundError:
            return DmarcMetricsCollection()

    def save(self, metrics: DmarcMetricsCollection):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(JSONSerializer.serialize(metrics), f)
