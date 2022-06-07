set -e

# python
python3 --version
pip3 install --upgrade linkediff

# coca
curl -LJO  https://github.com/modernizing/coca/releases/download/v2.3.0/coca_linux
mv ./coca_linux ./coca
chmod +x ./coca
./coca version

# run
linkediff init --to_xmind=./result.xmind --to_json=./result.json --coca_cmd=./coca
linkediff run
