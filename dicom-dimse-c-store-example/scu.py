import argparse
import os
from typing import Tuple
from pydicom import read_file
from pynetdicom import AE
from pynetdicom.presentation import PresentationContext
from logging import getLogger, basicConfig

basicConfig()
logger = getLogger(os.path.basename(os.path.dirname(__file__)))
logger.setLevel("INFO")


def send_c_store(ae: AE, dcm_path: str, scp_address: Tuple[str, int], idx: int) -> None:
    host, port = scp_address
    logger.debug(f"Establishing an association with DIMSE C-STORE SCP ({host}, {port})")

    dataset = read_file(dcm_path)
    abstract_syntax = dataset.file_meta[0x00020002].value
    transfer_syntax = dataset.file_meta[0x00020010].value

    context = PresentationContext()
    context.abstract_syntax = abstract_syntax
    context.transfer_syntax = [transfer_syntax]

    assoc = ae.associate(host, port, contexts=[context])
    if not assoc.is_established:
        logger.error("Failed to associate with SCP. Exiting...")
        assoc.release()
        return

    try:
        response = assoc.send_c_store(dataset)
        status = response[0x00000900].value
        dcm_file_name = os.path.basename(dcm_path)
        association_syntax = f"{abstract_syntax}{transfer_syntax}"
        logger.info(f"({idx}) Sent C-STORE '{dcm_file_name}' - syntax={association_syntax} - status={status}")
    finally:
        assoc.release()


def main() -> None:
    parser = argparse.ArgumentParser(description="Send C-STORE events to our DIMSE C-STORE SCP")
    parser.add_argument("path", type=str, help="Path to a directory of DICOM files/a single DICOM file")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="SCP hostname")
    parser.add_argument("--port", type=int, default=8081, help="SCP port")
    args = parser.parse_args()

    ae = AE(ae_title="SAMPLESCU")
    scp_address: Tuple[str, int] = (args.host, args.port)

    # CR Image Storage - At least one requested presentation context is required before associating with a peer.
    ae.add_requested_context("1.2.840.10008.5.1.4.1.1.1")

    path: str = os.path.abspath(os.path.expanduser(args.path))
    if os.path.isdir(path):
        logger.info(f"Walking directory... '{path}'")
        dcm_file_count = 0
        for root, dirs, files in os.walk(path):
            logger.info(f"Searching for .dcm files in '{root}':")
            for file in sorted(files):
                dcm_path = os.path.join(root, file)
                if not dcm_path.endswith(".dcm"):
                    continue

                send_c_store(ae, dcm_path, scp_address, dcm_file_count)
                dcm_file_count += 1
        return

    _, file_extension = os.path.splitext(path)
    if os.path.isfile(path) and file_extension == ".dcm":
        send_c_store(ae, path, scp_address, 1)
        return

    logger.error(f"Specified path must be a directory or DICOM file '{path}'")


if __name__ == "__main__":
    main()
