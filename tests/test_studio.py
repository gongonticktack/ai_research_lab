import io
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from PIL import Image
from lab import server

class StudioTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(server.app, base_url='http://127.0.0.1:8765')
        self.headers = {'Origin': 'http://127.0.0.1:8765'}

    def test_untrusted_origin_cannot_install(self):
        response = self.client.post('/api/install/triposr', headers={'Origin': 'https://untrusted.example'})
        self.assertEqual(response.status_code, 403)

    def test_untrusted_host_rejected(self):
        self.assertEqual(self.client.get('/api/models', headers={'Host': 'untrusted.example'}).status_code, 400)

    def test_missing_environment_and_unknown_model(self):
        with patch.object(server, 'installed', return_value=False):
            self.assertEqual(self.client.post('/api/generate/triposr', headers=self.headers, files={'image': ('image.png', b'bad', 'image/png')}).status_code, 409)
        self.assertEqual(self.client.post('/api/install/unknown', headers=self.headers).status_code, 404)

    def test_invalid_image_rejected(self):
        with patch.object(server, 'installed', return_value=True):
            response = self.client.post('/api/generate/triposr', headers=self.headers, files={'image': ('image.png', b'bad', 'image/png')})
        self.assertEqual(response.status_code, 400)

    def test_upload_job_and_artifact_contract(self):
        image = io.BytesIO()
        Image.new('RGB', (8, 8)).save(image, format='PNG')
        def fake_command(args, cwd, log, timeout=3600):
            if '-c' in args: return
            output = Path(args[args.index('--output-dir') + 1]) / '0'
            output.mkdir(parents=True)
            (output / 'mesh.glb').write_bytes(b'glTF-test-fixture')
        with tempfile.TemporaryDirectory() as tmp, patch.object(server, 'PRIVATE', Path(tmp)), patch.object(server, 'installed', return_value=True), patch.object(server, 'command', side_effect=fake_command):
            response = self.client.post('/api/generate/triposr', headers=self.headers, files={'image': ('image.png', image.getvalue(), 'image/png')})
            self.assertEqual(response.status_code, 200)
            jid = response.json()['id']
            for _ in range(100):
                state = self.client.get('/api/jobs/' + jid).json()
                if state['status'] != 'running': break
                time.sleep(.01)
            self.assertEqual(state['status'], 'completed')
            artifact = self.client.get(state['artifact'])
            self.assertEqual(artifact.content, b'glTF-test-fixture')
            self.assertTrue((Path(tmp) / jid / 'input.png').is_file())

    def test_concurrent_job_rejected(self):
        server.lock.acquire()
        try:
            self.assertEqual(self.client.post('/api/install/triposr', headers=self.headers).status_code, 409)
        finally:
            server.lock.release()
