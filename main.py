import re
import os
import yaml
import json
import html
import shutil
import argparse
import requests
import subprocess
from time import sleep
from bs4 import BeautifulSoup
from dotenv import load_dotenv

class WebsiteBuilder:
    def __init__(self, website_name):
        self.website_name = website_name
        self.session_token = os.getenv("codestitch_session")
        self.website_has_dark_mode = False
        self.cookies = {}
        if self.session_token:
            self.cookies["codestitch_session"] = self.session_token

    def get_dark_mode_styling(self):
        # Gets the dark mode css for dark.css 
        dark_mode_css_html = self.get_stitch_html_css(125)

        # Write only the css file
        self.save_to_file("dark", [dark_mode_css_html], write_html = False)

    def get_stitch_html_css(self, stitch_id):
        page_html = self.get_page_html(stitch_id)
        parser = BeautifulSoup(page_html, "html.parser")
        stitch_html_encoded = parser.select(".tab.active-tab .CODE-TEXTAREA")
        
        if len(stitch_html_encoded) == 0:
            raise Exception("Couldn't get the HTML from the stitch")

        stitch_html = html.unescape(stitch_html_encoded[0].text)

        css_a_tag = parser.find("a", class_="code_list_link", attrs={"data-codetype": "css"})
        code_id = int(css_a_tag["data-codeid"])

        # Checks if the dark mode if the user wants dark mode, and if it's available
        # If it is, then adds one to the code_id (the CSS codeid for dark mode is always the codeid + 1)
        if self.website_has_dark_mode:
            # Checks if the stitch has a dark mode
            if parser.find("input", id="css-theme-dark"):
                code_id += 1

        parent_div = parser.find_all("div", class_="tab", attrs={"data-codeid": str(code_id)})

        if len(parent_div) == 0:
            raise Exception(f"Couldn't find the div with the correct data-codeid: {code_id}")

        stitch_css_encoded = parent_div[0].find("textarea")
        stitch_css = html.unescape(stitch_css_encoded.text)

        js_a_tag = parser.find("a", class_="code_list_link", attrs={"data-codetype": "js"})
        if js_a_tag:
            code_id = js_a_tag["data-codeid"]
            parent_div = parser.find_all("div", class_="tab", attrs={"data-codeid": code_id})
            stitch_js_code = parent_div[0].find("textarea")
            stitch_js = html.unescape(stitch_js_code.text)
            return [stitch_html, stitch_css, stitch_js]

        return [stitch_html, stitch_css]

    def check_and_remove_directory(self):
        """Checks if directory exists and asks for confirmation before removing"""
        if os.path.exists(self.website_name):
            response = input(f"Directory '{self.website_name}' already exists. Do you want to delete it? (y/n): ")
            if response.lower() == 'y':
                print(f"Removing {self.website_name} directory...")
                shutil.rmtree(self.website_name)
                print("Directory removed.")
            else:
                print("Operation cancelled.")
                exit(1)

    def clone_and_setup_repository(self):
        """Clones the repository and sets up the project"""
        print("Cloning repository...")
        subprocess.run([
            "git", "clone",
            "https://github.com/RangerVinven/Intermediate-SASS-CodeStitch-Fork.git",
            self.website_name
        ], check=True)

        print("Removing git origin...")
        subprocess.run(["git", "remote", "remove", "origin"], 
                      cwd=self.website_name, 
                      check=True)

        print("Installing npm packages...")
        subprocess.run(["npm", "install"], 
                      cwd=self.website_name, 
                      check=True)

    def start_eleventy_server(self):
        """Starts the Eleventy server"""
        print("Starting Eleventy server...")
        subprocess.run(["npx", "@11ty/eleventy", "--serve"], 
                      cwd=self.website_name)

    def build(self, yaml_file):
        """Builds the entire website based on the YAML configuration"""
        # First check and potentially remove existing directory
        self.check_and_remove_directory()

        # Clone and setup repository
        self.clone_and_setup_repository()

        # Load website data using the static method
        website_data = WebsiteBuilder.parse_yaml_file(yaml_file)

        if website_data["Dark_Mode"]:
            self.website_has_dark_mode = True
            self.get_dark_mode_styling()
        
        # Get core styles
        print("Getting core styles...")
        self.get_core_styles(website_data["Navbar"])
        print("Core styles added!")

        # Create navbar
        if website_data["Navbar"]:
            print("Creating the navbar...")
            self.create_navbar(website_data["Navbar"])
            print("Navbar created!")

        # Create footer
        if website_data["Footer"]:
            print("Creating the footer...")
            self.create_footer(website_data["Footer"])
            print("Footer created!")

        # Create pages
        if not website_data["Pages"]:
            print("No pages found!")
            return

        for page in website_data["Pages"]:
            print(f"Creating {page['Page_Name']} page...")
            self.create_page(page["Page_Name"], page["Sections"])
            print("Page created!")

        print(f"Website created! Starting Eleventy server...")
        
        # Start the Eleventy server
        self.start_eleventy_server()

    def create_footer(self, stitch_id):
        stitch_html, stitch_css = self.get_stitch_html_css(stitch_id)
        
        with open(f"{self.website_name}/src/_includes/components/footer.html", "a") as f:
            f.write(stitch_html)

        with open(f"{self.website_name}/src/assets/css/root.css", "a") as f:
            f.write(stitch_css)

    def swap_html(self, old_html, html_to_swap_with, regex_pattern):
        return re.sub(
            regex_pattern,
            html_to_swap_with,
            old_html,
            flags=re.DOTALL
        )

    def swap_cs_ul_wrapper(self, stitch_html):
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
        return self.swap_html(stitch_html, new_html, pattern)

    def create_navbar(self, stitch_id):
        stitch_html, stitch_css, stitch_js = self.get_stitch_html_css(stitch_id)
        stitch_html = self.swap_cs_ul_wrapper(stitch_html)

        with open(f"{self.website_name}/src/_includes/components/header.html", "a") as f:
            f.write(stitch_html)

        with open(f"{self.website_name}/src/assets/css/root.css", "a") as f:
            f.write(stitch_css)

        with open(f"{self.website_name}/src/assets/js/nav.js", "a") as f:
            f.write(stitch_js)

    def get_page_html(self, stitch_id):
        url = f"https://codestitch.app/app/dashboard/stitches/{stitch_id}"
        response = requests.get(url, cookies=self.cookies)

        if response.status_code == 403:
            raise Exception("Server responded with 403 Forbidden. Is your codestitch_session correct? Check your .env file")
        
        if response.status_code == 404:
            raise Exception(f"Stitch {stitch_id} doesn't exist.")

        return response.content.decode()

    def get_core_styles(self, stitch_id):
        page_html = self.get_page_html(stitch_id)
        parser = BeautifulSoup(page_html, "html.parser")
        parent_div = parser.find_all("div", class_="tab", attrs={"data-codeid": "core-styles-CSS"})
        core_styles_encoded = parent_div[0].find("textarea")
        core_styles = html.unescape(core_styles_encoded.text)

        with open(f"{self.website_name}/src/assets/css/root.css", "a") as f:
            f.write(core_styles)

    def get_stitches(self, stitches):
        stitches_code = []
        for stitch in stitches:
            print(f"Getting {stitch}...")
            code = self.get_stitch_html_css(stitch)
            stitches_code.append(code)
            print(f"Got {stitch}!")
        return stitches_code

    def create_page(self, page_name, stitches, order=100):
        if page_name == "index":
            self.create_index_page(page_name, stitches)
            return

        stitches_code = self.get_stitches(stitches)
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

        with open(f"{self.website_name}/src/content/pages/{page_name}.html", "a") as f:
            f.write(front_matter)
            f.write("{% block head %}\n")
            f.write(f'<link rel="stylesheet" href="/assets/css/{page_name}.css" />')
            f.write("\n{% endblock %}\n")
            f.write("{% block body %}\n")

            for html_and_css in stitches_code:
                f.write(html_and_css[0])
                self.add_javascript(html_and_css, f)

            f.write("\n{% endblock %}\n")

        with open(f"{self.website_name}/src/assets/css/{page_name}.css", "a") as f:
            for html_and_css in stitches_code:
                f.write(html_and_css[1])

    def create_index_page(self, page_name, stitches):
        stitches_code = self.get_stitches(stitches)
        self.save_to_file(page_name, stitches_code)

    def add_javascript(self, stitches_code, file):
        if len(stitches_code) > 2:
            file.write("<script>")
            file.write(stitches_code[2])
            file.write("</script>")

    def save_to_file(self, page_name, html_and_css, write_html = True):
        html_file_path = f"{self.website_name}/src/{'content/pages/' if page_name != 'index' else ''}{page_name}.html"
        css_file_path = f"{self.website_name}/src/assets/css/{'local' if page_name == 'index' else page_name}.css"

        if write_html:
            with open(html_file_path, "a") as f:
                f.write("{% block body %}\n")
                for html_and_css_code in html_and_css:
                    f.write(html_and_css_code[0])
                    self.add_javascript(html_and_css_code, f)
                f.write("\n{% endblock %}\n")

        if page_name == "index":
            with open(f"{self.website_name}/src/assets/css/critical.css", "a") as f:
                f.write("\n")
                f.write(html_and_css[0][1])
                f.write("\n")
            html_and_css.pop(0)

        with open(css_file_path, "a") as f:
            for html_and_css_code in html_and_css:
                f.write(html_and_css_code[1])
                f.write("\n")

    @staticmethod
    def parse_yaml_file(file_name):
        with open(file_name, 'r') as yaml_file:
            return yaml.safe_load(yaml_file)

def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Generate a website from a YAML file.")
    parser.add_argument("file_name", type=str, help="The path to the YAML file containing the website data.")
    parser.add_argument("website_name", type=str, help="The name for the folder to put the website in.")
    args = parser.parse_args()

    website_builder = WebsiteBuilder(args.website_name)
    website_builder.build(args.file_name)

if __name__ == "__main__":
    main()
