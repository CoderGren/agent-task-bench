server.py is a tiny HTTP helper. test_server.py does not cover GET /health or several POST rejections.

Add tests only. Do not change server.py. New assertions must cover:
- GET /health returns 200 and a body of {"ok": true}
- POST /other returns 403
- a missing or wrong Content-Type returns 403
- a body of the wrong length (for example "{ }") returns 403
- the count is unchanged after each rejection
