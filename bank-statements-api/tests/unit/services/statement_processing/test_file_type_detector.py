from app.services.statement_processing.file_type_detector import StatementFileTypeDetector


class TestStatementFileTypeDetector:
    def test_detect_csv_file(self):
        detector = StatementFileTypeDetector()
        file_content = b"date,amount,description\n2023-01-01,100.00,Test transaction"
        file_type = detector.detect(file_content)
        assert file_type == "CSV"

    def test_detect_tsv_file(self):
        detector = StatementFileTypeDetector()
        file_content = b"date\tamount\tdescription\n2023-01-01\t100.00\tTest transaction"
        file_type = detector.detect(file_content)
        assert file_type == "TSV"

    def test_detect_tsv_file_with_commas_in_data(self):
        detector = StatementFileTypeDetector()
        file_content = b"date\tamount\tdescription\n2023-01-01\t1,234.56\tShop, Lisbon"
        file_type = detector.detect(file_content)
        assert file_type == "TSV"

    def test_detect_tsv_file_with_cp1252_encoding(self):
        detector = StatementFileTypeDetector()
        file_content = "Data\tDescrição\tMontante\n2024-01-01\tConta à ordem\t19,80".encode("cp1252")
        file_type = detector.detect(file_content)
        assert file_type == "TSV"

    def test_detect_tsv_file_behind_a_metadata_preamble(self):
        detector = StatementFileTypeDetector()
        preamble = (
            "Consultar extrato - 15-11-2026 : 0217005412400\r\n"
            "Nome empresa \tCONDOMINIO PREDIO SITO R LIMA 142\r\n"
            "Saldo contabil\u00edstico Inicial \t5.155,18 \r\n"
            "\r\n"
        )
        rows = "Data mov. \tDescri\u00e7\u00e3o \tMovimento \r\n08-11-2026\tCOM MANUTENCAO CONTA \t-10,40\r\n"
        file_content = (preamble + rows).encode("cp1252")

        assert detector.detect(file_content) == "TSV"

    def test_detect_csv_file_behind_a_metadata_preamble(self):
        detector = StatementFileTypeDetector()
        file_content = b"Account statement\r\nGenerated 2026-11-15\r\n\r\ndate,amount\r\n2026-11-08,-10.40\r\n"

        assert detector.detect(file_content) == "CSV"

    def test_a_stray_comma_in_the_preamble_does_not_outweigh_tabbed_data(self):
        detector = StatementFileTypeDetector()
        file_content = (
            "Extrato, conta \u00e0 ordem\r\n\r\nData\tDescri\u00e7\u00e3o\tMontante\r\n01-01-2026\tLoja\t19,80\r\n".encode(
                "cp1252"
            )
        )

        assert detector.detect(file_content) == "TSV"

    def test_detect_xlsx_file(self):
        detector = StatementFileTypeDetector()
        file_content = b"PK\x03\x04" + b"\x00" * 100
        file_type = detector.detect(file_content)
        assert file_type == "XLSX"

    def test_unknown_file_type(self):
        detector = StatementFileTypeDetector()
        file_content = b"This is not a CSV or XLSX file"
        file_type = detector.detect(file_content)
        assert file_type == "UNKNOWN"
