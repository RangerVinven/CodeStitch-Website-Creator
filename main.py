import re
import os
import html
import requests
from time import sleep
from bs4 import BeautifulSoup

def create_navbar(stitch_id):
    stitch_html, stitch_css, stitch_js = get_stitch_html_css(stitch_id)

    with open("website/src/_includes/components/header.html", "a") as f:
        f.write(stitch_html)

    with open("website/src/assets/css/", "a") as f:
        f.write(stitch_html)


def get_page_html(stitch_id):
    url = "https://codestitch.app/app/dashboard/stitches/" + str(stitch_id)
    response = requests.get(url)

    # If the session token is wrong
    if response.status_code == 403:
        raise Exception("Server responded with 403 Forbidden. Is your codestitch_session correct? Check your .env file")
    

    # Gets the entire page's contents
    page_html = response.content.decode()
    return page_html

def get_stitch_html_css(stitch_id):
    page_html = get_page_html(stitch_id)

    # Creates the parser and extracts the HTML
    parser = BeautifulSoup(page_html, "html.parser")
    stitch_html_encoded = parser.select(".tab.active-tab .CODE-TEXTAREA")
    
    # If we couldn't get the HTML
    if len(stitch_html_encoded) == 0:
        raise Exception("Couldn't get the HTML from the stitch")

    # Decodes the HTML (it's recieved URL encoded)
    stitch_html = html.unescape(stitch_html_encoded[0].text)

    # Gets the code_id
    css_a_tag = parser.find("a", class_="code_list_link", attrs={"data-codetype": "css"})
    code_id = css_a_tag["data-codeid"]

    # Gets the div with the textarea child with the css
    parent_div = parser.find_all("div", class_="tab", attrs={"data-codeid": code_id})

    if len(parent_div) == 0:
        raise Exception("Couldn't find the div with the correct data-codeid: " + str(code_id))

    # Gets the stitch's CSS
    stitch_css_encoded = parent_div[0].find("textarea")
    stitch_css = html.unescape(stitch_css_encoded.text)

    # Gets the core styles
    css_a_tag = parser.find("a", class_="code_list_link", attrs={"data-codetype": "core-styles"})

    # Gets the code_id
    js_a_tag = parser.find("a", class_="code_list_link", attrs={"data-codetype": "js"})
    if js_a_tag != None:
        code_id = js_a_tag["data-codeid"]

        # Gets the div with the textarea child with the css
        parent_div = parser.find_all("div", class_="tab", attrs={"data-codeid": code_id})

        # Gets the stitch's JS
        stitch_js_code = parent_div[0].find("textarea")
        stitch_js = html.unescape(stitch_js_code.text)
        
        return [stitch_html, stitch_css, stitch_js]

    return [stitch_html, stitch_css]

def get_core_styles(stitch_id):
    page_html = get_page_html(stitch_id)

    # Initalises the parser
    parser = BeautifulSoup(page_html, "html.parser")

    # Creates the parent_div
    parent_div = parser.find_all("div", class_="tab", attrs={"data-codeid": "core-styles-CSS"})
    core_styles_encoded = parent_div[0].find("textarea")

    # Decodes the core_styles
    core_styles = html.unescape(core_styles_encoded.text)

    # Saves it to the root.css file
    with open("website/src/assets/css/root.css", "a") as f:
        f.write(core_styles)


# Gets a list of the stitches
def get_stitches(stitches):
    stitches_code = []
    for stitch in stitches:
        print("Getting {}...".format(stitch))

        code = get_stitch_html_css(stitch)
        stitches_code.append(code)

        print("Got {}!".format(stitch))
        # sleep(0.5)

    return stitches_code

# Creates a page
def create_page(page_name, stitches):
    if page_name == "index":
        create_index_page(page_name, stitches)


# Creates an index page
def create_index_page(page_name, stitches):
    # Gets all the website's stitches
    stitches_code = get_stitches(stitches)
    save_to_file(page_name, stitches_code)

def save_to_file(page_name, html_and_css):
    # Sets the path of the HTML file
    html_file_path = ""
    css_file_path = ""
    if page_name == "index":
        html_file_path += "website/src/" + page_name + ".html"
        css_file_path += "website/src/assets/css/" + "local.css"

    else:
        html_file_path += "website/src/content/pages/" + page_name + ".html"
        css_file_path += "website/src/assets/css/" + page_name + ".css"

    # Saves the HTML to the file
    with open(html_file_path, "a") as f:
        f.write("{% block body %}\n")

        # Writes the HTML to the index file
        for html_and_css_code in html_and_css:
            f.write(html_and_css_code[0])

        f.write("\n{% endblock %}\n")

    # If the file is a home page, saves the hero's CSS to the critical file
    if page_name == "index":
        with open("website/src/assets/css/critical.css", "a") as f:
            f.write("\n")
            f.write(html_and_css[0][1])
            f.write("\n")

        # Removes the hero's code from the array
        html_and_css.pop(0)

    with open(css_file_path, "a") as f:
        for html_and_css_code in html_and_css:
            f.write(html_and_css_code[1])
            f.write("\n")

    print("Created website!")

# os.system("rm -r website;cp -r backup_website website")
stitches = [1946, 1666, 1446]
get_core_styles(stitches[0])
create_page("index", stitches)
# create_page("index", [1785, 1666])
