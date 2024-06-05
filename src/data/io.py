import sbol2


import dateutil.parser
from datetime import datetime

def format_datetime(dt_str):
    """
    Format the datetime string to the required format: YYYY-MM-DDTHH:MM:SS.000Z
    """
    dt = dateutil.parser.parse(dt_str)
    formatted_dt = dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    return formatted_dt

def normalize_datetime_fields(doc):
    """
    Normalize datetime fields in the SBOL document to the required format.
    """
    for obj in doc.SBOLObjects.values():
        if isinstance(obj, sbol2.Activity):
            if obj.endedAtTime:
                obj.endedAtTime = format_datetime(obj.endedAtTime)
            if obj.startedAtTime:
                obj.startedAtTime = format_datetime(obj.startedAtTime)
        # Add additional checks for other datetime fields if necessary

    return doc

def read_sbol_file(file_path):
    doc = sbol2.Document()
    postfix = file_path.split('.')[-1]
    # file_format = None
    # if postfix == 'rdf':
    #     file_format = 'rdfxml'
    # elif postfix == 'sbol':
    #     file_format = 'xml'
    doc.read(file_path)
    return doc

def write_sbol_file(doc, file_path):
    """
    Write the SBOL document to a file, ensuring that endedAtTime is set to None.
    """
    # Clear the endedAtTime field for all Activity objects. The time zone is not formatted correctly.
    # Not doing this leads to errors when importing the file with other programs (e.g. SBOLCanvas)
    for obj in doc.SBOLObjects.values():
        if isinstance(obj, sbol2.Activity):
            obj.endedAtTime = None

    # Determine the file format based on the file extension
    postfix = file_path.split('.')[-1]
    file_format = None
    if postfix in ['rdf', 'sbol']:
        file_format = 'xml'
    
    # Write the document to the file
    doc.write(file_path)



if __name__ == '__main__':
    file_to_read = '/Users/admin/repos/geneforge/data/syn_bio_hub/scraped/sbol/BBa_K318030.sbol'
    file_to_write = '/Users/admin/repos/geneforge/data/syn_bio_hub/BBa_K318030.xml'
    doc = read_sbol_file(file_to_read)
    write_sbol_file(doc, file_to_write)
    print(f'Wrote SBOL document to {file_to_write}')
    doc2 = read_sbol_file(file_to_write)

