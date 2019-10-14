import sys
import requests

# Example using curl
# curl localhost:8888/register_team -Fteam=cubic2 '-Fmembers=Sangtae Ha' '-Fmembers=Injong Rhee' '-Fmembers=Lisong Xu'

if len(sys.argv) < 3:
    print("Usage: python3 ./scripts/register.py team_name 'member 1 (email)' 'member 2 (email2)'")
    print("Example:")
    print("python3 ./scripts/register.py cubic 'Sangtae Ha (name1@example.com)' 'Injong Rhee (name2@example.com)' 'Lisong Xu (name3@example.com)'")
    # python3 ./scripts/register.py 'vegas' 'Lawrence Brakmo' 'Larry L. Peterson'
    sys.exit(0)

data = {'team': sys.argv[1],
        'members': sys.argv[2:]}

r = requests.post(url = 'http://localhost:8888/register_team', data = data)
print(r.content.decode())
