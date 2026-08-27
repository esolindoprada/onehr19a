from odoo import _, api, models
from odoo.exceptions import UserError, ValidationError


class HrAttendance(models.Model):
    """Narrow downstream bridge: canonical attendance remains owned by onehr_attendance/Odoo."""

    _inherit = "hr.attendance"

    @api.model
    def onehr_kiosk_apply_punch(self, device, kiosk_log):
        """Apply a kiosk punch through the accepted OneHR Attendance contract."""
        employee = kiosk_log.employee_id
        if not employee:
            raise ValidationError(_("Attendance punch requires a resolved employee."))
        if employee.company_id != device.company_id:
            raise ValidationError(_("Employee and kiosk device must belong to the same company."))

        open_attendance = self.search(
            [
                ("employee_id", "=", employee.id),
                ("check_out", "=", False),
            ],
            order="check_in desc, id desc",
            limit=1,
        )

        punch_mode = kiosk_log.punch_mode
        if punch_mode == "auto":
            punch_mode = "check_out" if open_attendance else "check_in"

        if punch_mode == "check_in":
            if open_attendance:
                raise UserError(
                    _("Employee is already checked in at %s.", open_attendance.check_in)
                )
            payload = {
                "employee_id": employee.id,
                "check_in": kiosk_log.event_at,
                "source_channel": "kiosk",
                "source_system": "ONEHR_KIOSK",
                "external_reference": f"{device.code}:{kiosk_log.client_event_id}",
                "device_reference": device.code,
                "in_mode": "kiosk",
            }
            if kiosk_log.latitude or kiosk_log.longitude:
                payload.update(
                    {
                        "in_latitude": kiosk_log.latitude,
                        "in_longitude": kiosk_log.longitude,
                        "in_location": (
                            device.work_location_id.display_name
                            if device.work_location_id
                            else device.display_name
                        ),
                    }
                )
            return self.onehr_ingest_interval(payload)

        if punch_mode != "check_out":
            raise ValidationError(_("Unsupported kiosk punch mode."))
        if not open_attendance:
            raise UserError(_("Employee has no open attendance to check out."))
        if kiosk_log.event_at <= open_attendance.check_in:
            raise ValidationError(_("Check Out must be later than Check In."))

        values = {
            "check_out": kiosk_log.event_at,
            "out_mode": "kiosk",
            "onehr_device_reference": device.code,
        }
        if kiosk_log.latitude or kiosk_log.longitude:
            values.update(
                {
                    "out_latitude": kiosk_log.latitude,
                    "out_longitude": kiosk_log.longitude,
                    "out_location": (
                        device.work_location_id.display_name
                        if device.work_location_id
                        else device.display_name
                    ),
                }
            )
        open_attendance.write(values)
        return open_attendance
