# esriOpenData-to-CKAN-mapper
Small python script for the mapping of an ArcGIS OpenData site to a CKAN instance with custom metadata

## System requirements
- Python 2.7
- A Web Server (IIS, Apache, etc.)

## Files
Here are the required files for the mapper to work

### EsriToCKAN.py
This is the python file to execute. The python file reads from the organisations.csv file to identify the organizations and urls required, then create several JSON files for the layers. It also create a "package_list.json" file that serves as an index for CKAN.

### EsriToCKAN.json
This is the JSON template. The python script uses that as a template for the output json files. The metadata schema is the one decided by the Government of Quebec's Open Data site (http://donneesquebec.ca)

### organisations.csv
This is the list of organizations to be processed. The name, id and ext-spatial fields are provided by the CKAN owner. The URL is the URL of an open data site, followed by /data.json. For example, you can acces the Shawinigan Open Data Site here https://donnees-shawinigan.opendata.arcgis.com . In the arcgisURl field, you would append data.json --> https://donnees-shawinigan.opendata.arcgis.com/data.json

### html2text.py
This is an html to markdown converter that is used to convert the description from ArcGIS Online (HTML) to CKAN (Markdown). Taken here: https://github.com/aaronsw/html2text
