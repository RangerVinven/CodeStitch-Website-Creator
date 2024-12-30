source venv/bin/activate
yes | rm -r website
git clone https://github.com/RangerVinven/Intermediate-SASS-CodeStitch-Fork.git website
cd website
git remote remove origin
npm install
cd ../
python3 main.py $1
cd website
npx @11ty/eleventy --serve
