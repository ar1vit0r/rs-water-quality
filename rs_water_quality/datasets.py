from dataclasses import dataclass


@dataclass(frozen=True)
class Dataset:
    indicator: str
    dataset_id: str
    unit: str
    count_column: str

    @property
    def url(self) -> str:
        return f"https://dadosabertos.ana.gov.br/datasets/{self.dataset_id}.csv"


DATASETS: tuple[Dataset, ...] = (
    Dataset(indicator="od", dataset_id="5d7db6cd8caf4116b69fa8185fe74b96_2", unit="mg/L", count_column="NUOD"),
    Dataset(indicator="dbo", dataset_id="d82c795398754609b0a8b4a550ef6c57_14", unit="mg/L", count_column="NUDBO"),
    Dataset(indicator="turbidez", dataset_id="97e46167e18c4fb0bda9dd5f8ed7783b_8", unit="NTU", count_column="NUTURB"),
    Dataset(indicator="fosforo_total", dataset_id="0419dd6718cb4be0a331c7589c57ea2b_5", unit="mg/L", count_column="NUP"),
    Dataset(indicator="ecoli", dataset_id="6a2d579dc3bd40838e7dbb9615324b93_17", unit="NMP/100 mL", count_column="NUECOLI"),
    Dataset(indicator="iqa", dataset_id="7a278de90bd14330ab014c9b5db350e0_17", unit="index 0-100", count_column="NUIQA"),
)
