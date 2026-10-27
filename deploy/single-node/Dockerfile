FROM debian:bookworm-slim@sha256:7ff6ba31527b9e336162fa061746c366c4b2032f4d2cff2078bea43f78efe3f8
COPY native /opt/native
COPY source /opt/fusion
ENV PATH=/opt/native/python/bin:/usr/bin:/bin \
    PYTHONPATH=/opt/fusion \
    PYTHONHOME=/opt/native/python \
    PYTHONDONTWRITEBYTECODE=1 \
    LD_LIBRARY_PATH=/opt/native/python/lib:/opt/native/swipl/lib/swipl/lib/x86_64-linux:/opt/native/deps \
    SWI_HOME_DIR=/opt/native/swipl/lib/swipl \
    HOME=/tmp \
    LANG=C.UTF-8
WORKDIR /opt/fusion
USER 1000:1000
ENTRYPOINT ["/opt/native/python/bin/python3.12", "-m", "integration.single_node.server"]
