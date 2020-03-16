from testfixtures import LogCapture


class LogCaptureHelper:
    @staticmethod
    def check_contain(log_capture: LogCapture, expected: tuple) -> bool:
        return expected in set(log_capture.actual())
