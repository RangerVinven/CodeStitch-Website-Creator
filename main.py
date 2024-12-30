import re
import os
import yaml
import json
import html
import argparse
import requests
from time import sleep
from bs4 import BeautifulSoup
from dotenv import load_dotenv

def create_footer(stitch_id, website_name):
    # Gets the HTML and CSS of the footer
    stitch_code = get_stitch_html_css(stitch_id)
    stitch_html = stitch_code[0]
    stitch_css = stitch_code[1]

    # Saves the footer HTML and CSS to their respective files
    with open("{}/src/_includes/components/footer.html".format(website_name), "a") as f:
        f.write(stitch_html)

    with open("{}/src/assets/css/root.css".format(website_name), "a") as f:
        f.write(stitch_css)

def swap_html(old_html, html_to_swap_with, regex_pattern):
    updated_html = re.sub(
        regex_pattern,
        # r'\1' + new_html + r'\3',  # Replace the middle group (inner content)
        html_to_swap_with,
        old_html,
        flags=re.DOTALL  # Ensures newlines are handled
    )

    return updated_html


# Swaps a div in the HTML to allow the navbar to work
def swap_cs_ul_wrapper(stitch_html):

    new_html = """
    <div class="cs-ul-wrapper">
                <ul id="cs-expanded" class="cs-ul">
                    {% set navPages = collections.all | eleventyNavigation %}

                    {# Loop through all pages with a eleventyNavigation in the frontmatter #}
                    {% for entry in navPages %}

                        {# Define a hasChild variable to make it easier to test what navigation items are have child dropdown pages #}
                        {% set hasChild = entry.children.length %}

                        {# Check the frontmatter for hideOnMobile/hideOnDesktop. Form a list of classes to be joined when the item is rendered #}
                        {% set hideClasses = [] %}
                        {% if entry.hideOnMobile %}
                            {% set hideClasses = (hideClasses.push("cs-hide-on-mobile"), hideClasses) %}
                        {% endif %}
                        {% if entry.hideOnDesktop %}
                            {% set hideClasses = (hideClasses.push("cs-hide-on-desktop"), hideClasses) %}
                        {% endif %}

                        {# If this page is a dropdown, give it the appropriate classes, icons and accessibility attributes #}
                        <li class="cs-li {% if hasChild %}cs-dropdown{% endif %} {{ hideClasses | join(" ") }}">
                            {# If the page has child dropdown pages, render it as a <button> tag with the appropriate dropdown HTML #}
                            {% if hasChild %}

                                {# Check to see if the user's current page is one of the child pages. If so, apply the cs-active class to the dropdown parent #}
                                {% set activeClass = "" %}
                                {% for child in entry.children %}
                                    {% if child.url == page.url %}
                                        {% set activeClass = "cs-active" %}
                                    {% endif %}
                                {% endfor %}

                                {# Render the <button> with the active class, dropdown icon and child links #}
                                <button
                                    class="cs-li-link cs-dropdown-button {{ activeClass }}"
                                    aria-expanded="false"
                                    aria-controls="dropdown-{{ entry.key }}"
                                    aria-label="dropdown-{{ entry.key }}"
                                >
                                    {{ entry.key }}
                                    <img
                                        class="cs-drop-icon"
                                        src="https://csimg.nyc3.cdn.digitaloceanspaces.com/Icons%2Fdown.svg"
                                        alt="dropdown icon"
                                        width="15"
                                        height="15"
                                        decoding="async"
                                        aria-hidden="true"
                                    />
                                </button>

                                {# Dropdowns have another ul/li set up within the parent li, which gets rendered in the same way as a normal link #}
                                <ul
                                    class="cs-drop-ul"
                                    id="dropdown-{{ entry.key }}"
                                >
                                    {% for child in entry.children %}
                                        <li class="cs-drop-li">
                                            <a
                                                href="{{ child.url }}"
                                                class="cs-li-link cs-drop-link"
                                                >{{ child.key }}</a
                                            >
                                        </li>
                                    {% endfor %}
                                </ul>
                            {% else %}
                                {# Normal pages are rendered as <a> tags, in the normal way you'd expect #}
                                <a
                                    href="{{ entry.url }}"
                                    class="cs-li-link {% if entry.url == page.url %}cs-active{% endif %}"
                                    {% if entry.url == page.url %}aria-current="page"{% endif %}
                                >
                                    {{ entry.key }}
                                </a>
                            {% endif %}
                        </li>
                    {% endfor %}
                </ul>
            </div>
    """

    pattern = r'<div class="cs-ul-wrapper">[\s\S]*?<\/div>'
    #
    # updated_html = re.sub(
    #     pattern,
    #     # r'\1' + new_html + r'\3',  # Replace the middle group (inner content)
    #     new_html,
    #     stitch_html,
    #     flags=re.DOTALL  # Ensures newlines are handled
    # )

# def swap_html(old_html, html_to_swap_with, regex_pattern):
    updated_html = swap_html(stitch_html, new_html, pattern)

    return updated_html

def create_navbar(stitch_id, website_name):
    stitch_html, stitch_css, stitch_js = get_stitch_html_css(stitch_id)

    stitch_html = swap_cs_ul_wrapper(stitch_html)

    with open("{}/src/_includes/components/header.html".format(website_name), "a") as f:
        f.write(stitch_html)

    with open("{}/src/assets/css/root.css".format(website_name), "a") as f:
        f.write(stitch_css)

    with open("{}/src/assets/js/nav.js".format(website_name), "a") as f:
        f.write(stitch_js)

def get_page_html(stitch_id):
    # Gets the session token if there's any
    session_token = os.getenv("codestitch_session")
    cookies = {}

    if session_token:
        cookies["codestitch_session"] = session_token

    url = "https://codestitch.app/app/dashboard/stitches/" + str(stitch_id)
    response = requests.get(url, cookies=cookies)

    # If the session token is wrong
    if response.status_code == 403:
        raise Exception("Server responded with 403 Forbidden. Is your codestitch_session correct? Check your .env file")
    
    if response.status_code == 404:
        raise Exception("Stitch {} doesn't exist.".format(stitch_id))

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

def get_core_styles(stitch_id, website_name):
    page_html = get_page_html(stitch_id)

    # Initalises the parser
    parser = BeautifulSoup(page_html, "html.parser")

    # Creates the parent_div
    parent_div = parser.find_all("div", class_="tab", attrs={"data-codeid": "core-styles-CSS"})
    core_styles_encoded = parent_div[0].find("textarea")

    # Decodes the core_styles
    core_styles = html.unescape(core_styles_encoded.text)

    # Saves it to the root.css file
    with open("{}/src/assets/css/root.css".format(website_name), "a") as f:
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
def create_page(page_name, stitches, website_name, order = 100):
    if page_name == "index":
        create_index_page(page_name, stitches, website_name)
        return

    stitches_code = get_stitches(stitches)

    # Creates the HTML and CSS files 
    pages_path = website_name + "/src/content/pages"
    # os.system("cp {}/_template.txt {}/{}.html".format(pages_path, pages_path, page_name))

    front_matter = f"""---
title: 'Page title for <title> and OG tags'
description: 'Description for <meta> description and OG tags'
preloadImg: '/assets/images/imagename.format'
permalink: '{page_name}/'
eleventyNavigation:
    key: {page_name.replace("_", " ").replace("-", " ").capitalize()}
    order: {order}
---

{{% extends "layouts/base.html" %}}

    """

    with open("{}/src/content/pages/{}.html".format(website_name, page_name), "a") as f:
        f.write(front_matter)
        f.write("{% block head %}\n")
        f.write('<link rel="stylesheet" href="/assets/css/{}.css" />'.format(page_name))
        f.write("\n{% endblock %}\n")
    
        f.write("{% block body %}\n")

        for html_and_css in stitches_code:
            f.write(html_and_css[0])
            add_javascript(html_and_css, f)

        f.write("\n{% endblock %}\n")

    with open("{}/src/assets/css/{}.css".format(website_name, page_name), "a") as f:
        for html_and_css in stitches_code:
            f.write(html_and_css[1])
        

# Creates an index page
def create_index_page(page_name, stitches, website_name):
    # Gets all the website's stitches
    stitches_code = get_stitches(stitches)
    save_to_file(page_name, stitches_code, website_name)

# Adds any JavaScript from the stitch
def add_javascript(stitches_code, file):
    if len(stitches_code) > 2:
        file.write("<script>")
        file.write(stitches_code[2])
        file.write("</script>")

def save_to_file(page_name, html_and_css, save_to_file, website_name):
    # Sets the path of the HTML file
    html_file_path = ""
    css_file_path = ""
    if page_name == "index":
        html_file_path += website_name + "/src/" + page_name + ".html"
        css_file_path += website_name + "/src/assets/css/" + "local.css"

    else:
        html_file_path += website_name + "/src/content/pages/" + page_name + ".html"
        css_file_path += website_name + "/src/assets/css/" + page_name + ".css"

    # Saves the HTML to the file
    with open(html_file_path, "a") as f:
        f.write("{% block body %}\n")

        # Writes the HTML to the index file
        for html_and_css_code in html_and_css:
            f.write(html_and_css_code[0])

            add_javascript(html_and_css_code, f) 

        f.write("\n{% endblock %}\n")

    # If the file is a home page, saves the hero's CSS to the critical file
    if page_name == "index":
        with open("{}/src/assets/css/critical.css".format(website_name), "a") as f:
            f.write("\n")
            f.write(html_and_css[0][1])
            f.write("\n")

        # Removes the hero's code from the array
        html_and_css.pop(0)

    with open(css_file_path, "a") as f:
        for html_and_css_code in html_and_css:
            f.write(html_and_css_code[1])
            f.write("\n")

def parse_yaml_file(file_name):
    file_data = None

    with open(file_name, 'r') as yaml_file:
        file_data = yaml.safe_load(yaml_file)

        # Convert to JSON
        # json_data = json.dumps(data, indent=4)

    return file_data

if __name__ == "__main__":
    # Loads the enviroment variables
    load_dotenv()

    # Sets up an argument parser
    parser = argparse.ArgumentParser(description="Generate a website from a YAML file.")
    parser.add_argument(
        "file_name", 
        type=str, 
        help="The path to the YAML file containing the website data."
    )
    parser.add_argument(
        "website_name", 
        type=str, 
        help="The name for the folder to put the website in."
    )
    args = parser.parse_args()

    # Gets the file name and website name
    file_name = args.file_name
    website_name = args.website_name

    # Gets the data from the YAML file
    website_data = parse_yaml_file(file_name)

    # Gets the core styles for any stitch (they're all the same)
    get_core_styles(website_data["Navbar"], website_name)

    # Creates the navbar  
    if website_data["Navbar"]:
        print("Creating the navbar...")
        create_navbar(website_data["Navbar"], website_name)
        print("Navbar created!")

    # Creates the footer  
    if website_data["Footer"]:
        print("Creating the footer...")
        create_footer(website_data["Footer"], website_name)
        print("Footer created!")

    # Exists the program if there's no pages provided (since there's nothing left to do)
    if not website_data["Pages"]:
        print("No pages found, goodebye!")
        exit

    for page in website_data["Pages"]:
        print("Creating {} page...".format(page["Page_Name"]))
        create_page(page["Page_Name"], page["Sections"], website_name)
        print("Page created!")

    print("Website created! Please look at the {}/ folder for your new website".format(website_name))

