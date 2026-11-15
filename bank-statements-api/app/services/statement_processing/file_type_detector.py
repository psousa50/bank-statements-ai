from app.services.statement_processing.text_decoding import decode_statement_bytes

SCANNED_LINES = 25


class StatementFileTypeDetector:
    def detect(self, file_content: bytes) -> str:
        if file_content.startswith(b"PK\x03\x04"):
            return "XLSX"

        if b"\n" not in file_content:
            return "UNKNOWN"

        lines = [line for line in decode_statement_bytes(file_content).splitlines() if line.strip()][:SCANNED_LINES]
        if not lines:
            return "UNKNOWN"

        tabs = sum(line.count("\t") for line in lines)
        commas = sum(line.count(",") for line in lines)

        if tabs and tabs >= commas:
            return "TSV"
        if commas:
            return "CSV"

        return "UNKNOWN"
