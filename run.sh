source venv/bin/activate
# yes | rm -r $2
git clone https://github.com/RangerVinven/Intermediate-SASS-CodeStitch-Fork.git $2
cd $2
git remote remove origin
npm install
cd ../
python3 main.py $1 $2
cd $2
npx @11ty/eleventy --serve
