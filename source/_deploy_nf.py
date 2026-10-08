import json, base64, urllib.request, os

TOKEN = 'nfp_KFGJuqf7YZDNkoysmXLW8hoaYwEJnkhjcce4'
SITE_ID = '2a256a74-d6d6-420c-b4eb-deb83ce13c11'

def deploy():
    zip_path = 'd:/zcy/ai_ty/packages/deploy.zip'
    if not os.path.exists(zip_path):
        print('deploy.zip not found')
        return

    with open(zip_path, 'rb') as f:
        data = f.read()

    req = urllib.request.Request(
        f'https://api.netlify.com/api/v1/sites/{SITE_ID}/deploys',
        data=data, method='POST',
        headers={
            'Authorization': f'Bearer {TOKEN}',
            'Content-Type': 'application/zip',
        }
    )
    try:
        with urllib.request.urlopen(req) as r:
            resp = json.loads(r.read())
            print(f"State: {resp.get('state')}, URL: {resp.get('ssl_url')}")
    except Exception as e:
        print(f'Error: {e}')
        if hasattr(e, 'read'):
            print(e.read().decode()[:300])

if __name__ == '__main__':
    deploy()
