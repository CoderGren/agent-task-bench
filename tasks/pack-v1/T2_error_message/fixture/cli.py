def request(command, color, lights=None):
    allowed_set = {"white", "red"}
    allowed_group = {"white", "red", "off"}
    if command == "set_group":
        if color not in allowed_group:
            raise ValueError("color must be white or red")
        return {"ok": True, "command": command, "color": color, "lights": lights}
    if command == "set":
        if color not in allowed_set:
            raise ValueError("color must be white or red")
        return {"ok": True, "command": command, "color": color}
    raise ValueError("unknown command")
