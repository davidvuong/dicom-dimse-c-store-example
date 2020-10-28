import os
from datetime import datetime
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Union, cast
from logging import getLogger, basicConfig
from pydicom.datadict import dictionary_VM, dictionary_VR
from pydicom.dataset import FileDataset
from pydicom.multival import MultiValue
from pydicom.sequence import Sequence
from pydicom.uid import generate_uid
from pynetdicom.sop_class import VerificationSOPClass
from pynetdicom import events, AE, DEFAULT_TRANSFER_SYNTAXES, ALL_TRANSFER_SYNTAXES
from pynetdicom.events import Event
from pynetdicom import sop_class

basicConfig()
logger = getLogger(os.path.basename(os.path.dirname(__file__)))
logger.setLevel("INFO")


@dataclass
class SCPConfig:
    implementation_class_uid: str
    port: int


def to_dicom_tag(tag: int, padding: int = 10) -> str:
    return f"{tag:#0{padding}x}"


def parse_da_vr(value: str) -> Optional[datetime]:
    for format in ("%Y%m%d", "%Y-%m-%d", "%Y:%m:%d"):
        try:
            return datetime.strptime(value, format)
        except ValueError:
            pass
    return None


ParsedElementValue_ = Union[str, float, int, datetime]
ParsedElementValue = Union[List[ParsedElementValue_], ParsedElementValue_]

DicomVRParseDictionary: Dict[str, Callable[[str], Optional[ParsedElementValue_]]] = {
    "DA": parse_da_vr,
    "DS": lambda value: float(value),
    "TM": lambda value: float(value),
    "US": lambda value: int(value),
    "IS": lambda value: int(value),
    "PN": lambda value: value.encode("utf-8").decode("utf-8"),
}


def safe_get_(dcm: FileDataset, tag: int) -> Optional[ParsedElementValue]:
    try:
        element = dcm[tag]
        VR, element_value = dictionary_VR(tag), element.value

        if element_value == "" or element_value is None:
            return None

        vr_parser = DicomVRParseDictionary.get(VR, lambda value: value)
        if isinstance(element_value, MultiValue) is not isinstance(element_value, Sequence):
            return cast(ParsedElementValue, [vr_parser(item) for item in element_value])

        return vr_parser(element_value)
    except KeyError:
        logger.debug(f"Cannot find element using for tag={to_dicom_tag(tag)}")
        return None
    except ValueError as error:
        logger.warning(f"Encountered ValueError extracting element for tag={to_dicom_tag(tag)} - err={error}")
        return None


def safe_get(dcm: FileDataset, tag: int) -> Optional[ParsedElementValue]:
    element = safe_get_(dcm, tag)
    VM: str = dictionary_VM(tag)
    return [] if element is None and VM != "1" else element


class SCP:
    def __init__(self, aet: str, config: SCPConfig) -> None:
        self.config = config
        self.address = ("0.0.0.0", config.port)

        self.ae = AE(ae_title=aet)
        self.ae.implementation_class_uid = config.implementation_class_uid
        self.ae.implementation_version_name = f'{aet}_{config.implementation_class_uid.split(".")[-1]}'[:16]

        self.SUPPORTED_ABSTRACT_SYNTAXES: List[str] = [
            sop_class.DigitalXRayImagePresentationStorage,
            sop_class.DigitalXRayImageProcessingStorage,
            sop_class.CTImageStorage,
        ]
        for abstract_syntax in self.SUPPORTED_ABSTRACT_SYNTAXES:
            self.ae.add_supported_context(abstract_syntax, ALL_TRANSFER_SYNTAXES)
        self.ae.add_supported_context(VerificationSOPClass, DEFAULT_TRANSFER_SYNTAXES)

        self.ae.require_calling_aet = ["SAMPLESCU"]

    def handle_c_store(self, event: Event) -> int:
        ds = event.dataset
        ds.file_meta = event.file_meta

        metadata: Dict[str, Optional[ParsedElementValue]] = {
            "CallingAET": cast(str, event.assoc.requestor.ae_title.strip()),
            "SopInstanceUID": safe_get(ds, 0x00080018),
            "StudyInstanceUID": safe_get(ds, 0x0020000D),
            "Modality": safe_get(ds, 0x00080060),
        }
        log_message_meta = " - ".join([f"{k}={v}" for k, v in metadata.items() if v])
        logger.info(f"Processed C-STORE {log_message_meta}")

        return 0x0000

    def start(self) -> None:
        logger.info(f"Starting DIMSE C-STORE AE on address={self.address} aet={self.ae.ae_title}")
        self.handlers = [(events.EVT_C_STORE, self.handle_c_store)]
        self.ae.start_server(self.address, block=True, evt_handlers=self.handlers)


def main() -> None:
    config = SCPConfig(implementation_class_uid=generate_uid(), port=8081)
    server = SCP("SAMPLESCP", config)
    server.start()


if __name__ == "__main__":
    main()
