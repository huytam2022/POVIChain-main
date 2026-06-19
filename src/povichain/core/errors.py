class PoVIError(Exception):
    pass


class SchemaError(PoVIError):
    pass


class CalibrationError(PoVIError):
    pass


class ManifestError(PoVIError):
    pass


class DispatcherError(PoVIError):
    pass


class DeterminismError(PoVIError):
    pass


class InsufficientCalibrationLength(CalibrationError):
    pass
