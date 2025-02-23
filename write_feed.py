import time
from xml.etree.ElementTree import Element, SubElement, ElementTree, tostring, parse
from xml.dom.minidom import parseString

def append_to_feed(title, url, filename):
    # domain needs to come from env var
    domain = "http://127.0.0.1:5000"
    try:
        # Get the file size in bytes
        file_path = os.path.join('mp3', filename)
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0

        # Parse or create the RSS feed.xml
        tree = parse("feed.xml")
        root = tree.getroot()
    except FileNotFoundError:
        # If feed.xml does not exist, initialize a new root with namespaces
        root = Element("rss", {
            'version': "2.0",
            'xmlns:dc': "http://purl.org/dc/elements/1.1/",
            'xmlns:itunes': "http://www.itunes.com/dtds/podcast-1.0.dtd"
        })
        channel = SubElement(root, "channel")
        
        # Add channel metadata
        SubElement(channel, "title").text = "Article Reader Podcast"
        SubElement(channel, "link").text = "https://github.com/aedocw/reader-podcast"
        SubElement(channel, "description").text = "This is a podcast created with https://github.com/aedocw/reader-podcast"
        owner = SubElement(channel, "itunes:owner")
        SubElement(owner, "itunes:name").text = "Owner Name"
        SubElement(owner, "itunes:email").text = "owner@example.com"
        SubElement(channel, "itunes:block").text = "Yes"
        SubElement(channel, "itunes:keywords").text = ""
        
        image = SubElement(channel, "image")
        SubElement(image, "title").text = "Podcast Logo"
        SubElement(image, "url").text = f"{domain}/logo.png"
        SubElement(image, "link").text = f"{domain}"
        SubElement(image, "width").text = "-1"
        SubElement(image, "height").text = "-1"
        
    channel = root.find("channel")

    # Create a new item for the episode
    item = SubElement(channel, "item")
    SubElement(item, "title").text = title
    SubElement(item, "link").text = url
    SubElement(item, "description").text = f"This episode is titled '{title}' and is available at {url}."
    
    # Corrected Enclosure URL
    audio_url = f"{domain}/mp3/{filename}"
    enclosure = SubElement(item, "enclosure", {
        "url": audio_url,
        "length": str(file_size),
        "type": "audio/mpeg"
    })
    
    pub_date_str = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
    SubElement(item, "pubDate").text = pub_date_str
    SubElement(item, "guid", isPermaLink="false").text = filename
    SubElement(item, "dc:date").text = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Generate and pretty-print the XML
    xml_str = tostring(root, encoding='utf-8').decode('utf-8')
    pretty_xml_str = parseString(xml_str).toprettyxml(indent="  ", newl="\n")
    
    # Write the pretty-printed XML to the file
    with open("feed.xml", "w", encoding="utf-8") as f:
        f.write(pretty_xml_str.strip())

