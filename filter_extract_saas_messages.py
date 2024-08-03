import re
from collections import Counter
import pandas as pd


# helper function to account for alternative patterns in suburb punctuation
def create_alternative_patterns(suburb):
    suburb_escaped = re.escape(suburb)
    suburb_no_specials = re.escape(re.sub(r'[^A-Za-z0-9\s]', '', suburb))
    return f'{suburb_escaped}|{suburb_no_specials}'


# main wrapper function
def import_extract_saas_messages(filepath) -> pd.DataFrame:
    df = pd.read_csv(filepath)
    
    # filter results to only agency "30" ["South Australian Ambulance Service/SAAS"]
    df = df[df['agency'] == 30]

    # reformat the date time column
    df['datetime'] = pd.to_datetime(df['date time'], format="%d-%m-%Y %H_%M_%S")

    # rename the message id column
    df = df.rename(columns={'message id': 'id'})

    # tidy the columns, drop "agency" as it's no longer required.
    df = df[['id', 'datetime', 'message']]
    
    # non-job related messages can be safely dropped
    df = df[df['message'].str.contains('PR:')].reset_index(drop=True)

    # extract the "unit" identifier
    df['unit'] = df['message'].apply(lambda x: x.split(' ')[0])

    # extract the "priority" level
    df['priority'] = df['message'].apply(lambda x: x.split('-')[0].split('PR:')[-1].strip())

    # residential or public "location" boolean
    df['residential'] = ~df['message'].str.contains('@')

    # extract the job "description" (find the "dispatch time" and extract the text that follows)
    df['event'] = df['message'].str.split(r'\b\d\d:\d\d\b', regex=True).apply(lambda x: x[-1])
    
    # import the list of South Australian suburbs
    suburbs = pd.read_csv('SA_suburbs.csv', usecols=['suburb'])['suburb'].tolist()
    
    # Compile the pattern with word boundaries to exact match whole words
    suburb_pattern = '|'.join(create_alternative_patterns(suburb) for suburb in sorted(suburbs, key=len, reverse=True))
    suburb_regex = re.compile(r'\b(' + suburb_pattern + r')\b', re.IGNORECASE)
    
    # helper function to extract/match the suburb from the message
    def find_suburb(message):

        matches = suburb_regex.findall(message)
        if matches:
            # Count occurrences of each matched suburb
            match_counts = Counter(matches)
            # Return the suburb with the highest count
            return match_counts.most_common(1)[0][0]
        return None
    
    # apply the matching function to all messages
    df['matched_suburb'] = df['message'].apply(find_suburb)
    
    return df


if __name__ == "__main__":
    df = import_extract_saas_messages(filepath='sample_messages.csv')
    print(df.shape)