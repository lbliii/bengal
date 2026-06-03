Fixed a dev-server (`bengal serve`) crash where serving a static asset (CSS/JS/font) could
abort the worker with `BlockingIOError: [Errno 35] Resource temporarily unavailable`. The dev
server disables compression so live-reload streams immediately, which makes Pounce advertise
its zero-copy `pounce.sendfile` extension; Pounce 0.7.1's sendfile path runs `os.sendfile` in
a thread executor without handling `EAGAIN` on the non-blocking socket, so a full send buffer
crashed the transfer (seen on macOS + free-threaded CPython 3.14t). Bengal now opts out of the
`pounce.sendfile` extension for dev static serving, falling back to chunked ASGI body writes
that respect async backpressure. The production-like preview server keeps compression (and so
never advertised sendfile) and is unaffected. Tracked upstream as
[lbliii/pounce#72](https://github.com/lbliii/pounce/issues/72).
