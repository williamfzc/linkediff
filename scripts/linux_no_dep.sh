set -e

PATCH_FILE="diff.patch"

# python
python3 --version
pip3 install --upgrade linkediff

# coca
curl -LJO  https://github.com/modernizing/coca/releases/download/v2.3.0/coca_linux
mv ./coca_linux ./coca
chmod +x ./coca
./coca version

# diff
git status
git diff HEAD~3 HEAD > ${PATCH_FILE}

# run
linkediff init --patch_file=./${PATCH_FILE} --to_xmind=./result.xmind --to_json=./result.json --coca_cmd=./coca
linkediff run
