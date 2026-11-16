#!/bin/sh
set -e
python -u -c "import mock_server; mock_server.app.run(host='0.0.0.0', port=8001, debug=False)" &
python -u -c "import mock_server; mock_server.app.run(host='0.0.0.0', port=8000, debug=False)" &
wait
