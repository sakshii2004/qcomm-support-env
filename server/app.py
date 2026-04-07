# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
FastAPI application for the Qcomm Support Env Environment.

This module creates an HTTP server that exposes the QcommSupportEnvironment
over HTTP and WebSocket endpoints, compatible with EnvClient.
"""

try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:  # pragma: no cover
    raise ImportError(
        "openenv is required for the web interface. Install dependencies with '\n    uv sync\n'"
    ) from e

try:
    from ..models import QCommSupportAction, QCommSupportObservation
    from .qcomm_support_env_environment import QcommSupportEnvironment
except ImportError:
    from models import QCommSupportAction, QCommSupportObservation
    from server.qcomm_support_env_environment import QcommSupportEnvironment


# Create the app with web interface and README integration
app = create_app(
    QcommSupportEnvironment,
    QCommSupportAction,
    QCommSupportObservation,
    env_name="qcomm_support_env",
    max_concurrent_envs=4,
)


def main():
    """Entry point for direct execution."""
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address")
    parser.add_argument("--port", type=int, default=8000, help="Port number")
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
