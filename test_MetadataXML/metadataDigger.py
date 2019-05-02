
def getMetadata(itemID):
    import requests
    from xml.etree import ElementTree
    r = requests.get("https://www.arcgis.com/sharing/rest/content/items/"+itemID+"/info/metadata/metadata.xml?format=default")
    print("code: " + str(r.status_code))
    tree = ElementTree.fromstring(r.content)
    taggs = []
    tagsXML = tree.findall('idinfo')[0].findall('keywords')[0].findall('theme')[0].findall('themekey')
    print("Liste de tags: ")
    for item in tagsXML:
        print("\t" + item.text)
        taggs.append(item.text)
    abstract = tree.findall('idinfo')[0].findall('descript')[0].findall('abstract')[0].text
    print("Abstract: " + abstract)
    purpose = tree.findall('idinfo')[0].findall('descript')[0].findall('purpose')[0].text
    print("Purpose: " + purpose)
    freqUpdate = tree.findall('idinfo')[0].findall('status')[0].findall('update')[0].text
    print("Freq update: " + freqUpdate)
    return abstract,purpose,taggs, freqUpdate


abstract, purpose, taggs, freqUpdate = getMetadata("7804d76931994ec19104050d0177a0b4")