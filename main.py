import re
import html
import requests
from time import sleep
from bs4 import BeautifulSoup

def get_stitch_html_css(stitch_id):
    url = "https://codestitch.app/app/dashboard/stitches/" + str(stitch_id)
    response = requests.get(url)

    # If the session token is wrong
    if response.status_code == 403:
        raise Exception("Server responded with 403 Forbidden. Is your codestitch_session correct? Check your .env file")
    

    # Gets the entire page's contents
    page_html = response.content.decode()

    # Creates the parser and extracts the HTML
    parser = BeautifulSoup(page_html, "html.parser")
    stitch_html_encoded = parser.select(".tab.active-tab .CODE-TEXTAREA")
    
    # If we couldn't get the HTML
    if len(stitch_html_encoded) == 0:
        raise Exception("Couldn't get the HTML from the stitch")

    # Decodes the HTML (it's recieved URL encoded)
    stitch_html = html.unescape(stitch_html_encoded[0].text)

    # Gets the CSS navbar item
    # stitch_navbar_items = parser.select("code_list__item")
    stitch_navbar_items = parser.find_all("li", class_="code_list__item")

    # If we couldn't get the css navbar item
    if len(stitch_navbar_items) < 2:
        raise Exception("Couldn't get the CSS navbar item")

    # Gets the a tag with the data-codeid attribute
    stitch_css_item = stitch_navbar_items[-2].find("a")

    if "data-codeid" not in stitch_css_item.attrs:
        raise Exception("Couldn't get the CSS's codeid (used to find the codeblock for the CSS)")

    # Gets the code_id
    code_id = stitch_css_item["data-codeid"]

    # Gets the div with the textarea child with the css
    parent_div = parser.find_all("div", class_="tab", attrs={"data-codeid": code_id})

    if len(parent_div) == 0:
        raise Exception("Couldn't find the div with the correct data-codeid: " + str(code_id))

    # Gets the stitch's CSS
    stitch_css_encoded = parent_div[0].find("textarea")
    stitch_css = html.unescape(stitch_css_encoded.text)

    return (stitch_html, stitch_css)
    
# Gets a list of the stitches
def get_stitches(stitches):
    stitches_code = []
    for stitch in stitches:
        print("Getting {}...".format(stitch))

        code = get_stitch_html_css(stitch)
        stitches_code.append(code)

        print("Got {}!".format(stitch))
        sleep(0.5)

    return stitches_code

# Creates a page
def create_page(page_name, stitches):
    if page_name == "index":
        create_index_page(page_name, stitches)

# Creates an index page
def create_index_page(page_name, stitches):
    # Gets all the website's stitches
    stitches_code = get_stitches(stitches)
    save_to_file(stitches_code)

def save_to_file(html_and_css):
    with open("index.html", "a") as f:
        f.write("{% block body %}\n")

        # Writes the HTML to the index file
        for html_and_css_code in html_and_css:
            f.write(html_and_css_code[0])

        f.write("\n{% endblock %}\n")

# code = get_stitch_html_css(2051)
# print(code)

create_page("index", [1785, 1666, 1446])
