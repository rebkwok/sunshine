from django.test import TestCase
from booking.widgets import DurationSelectorWidget


class DurationSelectorWidgetTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.widget = DurationSelectorWidget()

    def test_get_duration_hours_from_widget(self):
        weeks = 1
        days = 4
        hours = 23
        total_hours = weeks * 7 * 24 + days * 24 + hours

        data = {'cancellation_period_0': weeks,
                'cancellation_period_1': days,
                'cancellation_period_2': hours}
        duration_hours = self.widget.value_from_datadict(
            data, {}, 'cancellation_period'
        )
        self.assertEqual(total_hours, duration_hours)

    def test_decompress(self):
        converted_duration = self.widget.decompress(619)
        weeks_days_hours = [3, 4, 19]
        self.assertEqual(weeks_days_hours, converted_duration)

    def test_decompress_with_no_value(self):
        converted_duration = self.widget.decompress("")
        self.assertEqual([None, None, None], converted_duration)

    def test_format_output(self):
        output = self.widget.format_output(self.widget.widgets)
        self.assertIn("Weeks:", output)
        self.assertIn("Days:", output)
        self.assertIn("Hours:", output)
