In cli.py, the `set_group` command accepts white, red, or off. The error message still says "color must be white or red". Make the message accurate for `set_group` only. The `set` command must still say "color must be white or red".

Do not change the validation logic or the accepted values. Add a test in test_cli.py that:
- calling request("set_group", "blue") raises ValueError mentioning off
- calling request("set", "blue") still says "white or red" and does not mention off
