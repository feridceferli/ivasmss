import unittest
from group_sms_redaction import redact_group_sms

class GroupSMSRedactionTests(unittest.TestCase):
    def test_sample(self):
        self.assertEqual(redact_group_sms('SIGNIUS token: 705031', '705031'), 'SIGNIUS token: ••••••')

    def test_multiple_code_mentions(self):
        value = redact_group_sms('Code 705031. Use OTP 705031 to log in.', '705031')
        self.assertNotIn('705031', value)
        self.assertIn('Use OTP', value)

    def test_spaced_code(self):
        self.assertNotIn('705 031', redact_group_sms('Your code: 705 031', '705031'))

    def test_unrecognized_otp(self):
        self.assertEqual(redact_group_sms('Verification code: 123456', 'N/A'), 'Verification code: ••••••')

    def test_link(self):
        self.assertNotIn('https://', redact_group_sms('Sign in: https://example.net/login?t=abc123', 'N/A'))

    def test_empty(self):
        self.assertEqual(redact_group_sms(None, ''), 'SMS mətni yoxdur')

if __name__ == '__main__':
    unittest.main()
