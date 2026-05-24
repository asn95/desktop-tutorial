"""Global maintenance mode state."""


class _MaintenanceState:
    def __init__(self):
        self.enabled = False
        self.message = "System is under maintenance. Please try again later."

    def toggle(self, enabled: bool, message: str | None = None):
        self.enabled = enabled
        if message:
            self.message = message


maintenance_state = _MaintenanceState()
