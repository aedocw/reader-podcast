import time
from xml.etree.ElementTree import Element, SubElement, ElementTree, tostring, parse
from xml.dom.minidom import parseString

def append_to_feed(title, url, filename):
    try:
        # Try to load the existing feed
        tree = parse("feed.xml")
        root = tree.getroot()
    except FileNotFoundError:
        # If the feed doesn't exist, create a new one
        root = Element("rss")
        root.set("version", "2.0")
        channel = SubElement(root, "channel")
        
        # Add channel metadata
        SubElement(channel, "title").text = "My articles to listen to"
        SubElement(channel, "link").text = "htts://pods.aedo.net"
        SubElement(channel, "description").text = "These are podcasts of articles I want to listen to"
        
    channel = root.find("channel")

    # Create a new item for the episode
    item = SubElement(channel, "item")
    SubElement(item, "title").text = title
    SubElement(item, "link").text = url
    SubElement(item, "guid").text = filename
    SubElement(item, "pubDate").text = time.strftime("%a, %d %b %Y %H:%M:%S %z", time.gmtime())
    
    # Generate and pretty-print the XML
    xml_str = tostring(root, encoding='utf-8').decode('utf-8')
    pretty_xml_str = parseString(xml_str).toprettyxml(indent="  ", newl="\n")
    
    # Write the pretty-printed XML to the file
    with open("feed.xml", "w", encoding="utf-8") as f:
        f.write(pretty_xml_str.strip())