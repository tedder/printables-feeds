import requests
import datetime
import json
import tempfile
import boto3

def request_printables(ordering=''):
    url = 'https://api.printables.com/graphql/'
    # headers are leftover from reverse-engineering, all I know is it works as is.
    headers = {
        'accept': 'application/graphql-response+json, application/graphql+json, application/json, text/event-stream, multipart/mixed',
        'accept-language': 'en',
        #'authorization': 'Bearer eyJhbGciO..',
        #'client-uid': '52ef2ef8-ec4a-477e-..',
        'content-type': 'application/json',
        #'dnt': '1',
        'graphql-client-version': 'v1.0.96',
        'origin': 'https://www.printables.com',
        #'priority': 'u=1, i',
        #'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        #'sec-ch-ua-mobile': '?0',
        #'sec-ch-ua-platform': '"macOS"',
        #'sec-fetch-dest': 'empty',
        #'sec-fetch-mode': 'cors',
        #'sec-fetch-site': 'same-site',
        #'sec-gpc': '1',
        'user-agent': 'RSS feed scraper (contact ted@tedder.me)'
        #'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
    }

    data = {
        "operationName": "ModelList",
        "query": """query ModelList($limit: Int!, $cursor: String, $categoryId: ID, $materialIds: [Int], $userId: ID, $printerIds: [Int], $licenses: [ID], $ordering: String, $hasModel: Boolean, $filesType: [FilterPrintFilesTypeEnum], $includeUserGcodes: Boolean, $nozzleDiameters: [Float], $weight: IntervalObject, $printDuration: IntervalObject, $publishedDateLimitDays: Int, $featured: Boolean, $featuredNow: Boolean, $usedMaterial: IntervalObject, $hasMake: Boolean, $competitionAwarded: Boolean, $onlyFollowing: Boolean, $collectedByMe: Boolean, $madeByMe: Boolean, $likedByMe: Boolean, $paid: PaidEnum, $price: IntervalObject, $downloadable: Boolean, $excludedIds: [ID]) {
            models: morePrints(
                limit: $limit
                cursor: $cursor
                categoryId: $categoryId
                materialIds: $materialIds
                printerIds: $printerIds
                licenses: $licenses
                userId: $userId
                ordering: $ordering
                hasModel: $hasModel
                filesType: $filesType
                nozzleDiameters: $nozzleDiameters
                includeUserGcodes: $includeUserGcodes
                weight: $weight
                printDuration: $printDuration
                publishedDateLimitDays: $publishedDateLimitDays
                featured: $featured
                featuredNow: $featuredNow
                usedMaterial: $usedMaterial
                hasMake: $hasMake
                onlyFollowing: $onlyFollowing
                competitionAwarded: $competitionAwarded
                collectedByMe: $collectedByMe
                madeByMe: $madeByMe
                liked: $likedByMe
                paid: $paid
                price: $price
                downloadablePremium: $downloadable
                excludedIds: $excludedIds
            ) {
                cursor
                items {
                    ...Model
                    __typename
                }
                __typename
            }
        }
        fragment AvatarUser on UserType {
            id
            handle
            verified
            dateVerified
            publicUsername
            avatarFilePath
            badgesProfileLevel {
                profileLevel
                __typename
            }
            __typename
        }
        fragment LatestContestResult on PrintType {
            latestContestResult: latestCompetitionResult {
                ranking: placement
                competitionId
                __typename
            }
            __typename
        }
        fragment Model on PrintType {
            id
            name
            slug
            ratingAvg
            likesCount
            liked
            datePublished
            dateFeatured
            firstPublish
            downloadCount
            mmu
            category {
                id
                path {
                    id
                    name
                    nameEn
                    __typename
                }
                __typename
            }
            modified
            image {
                ...SimpleImage
                __typename
            }
            nsfw
            club: premium
            price
            user {
                ...AvatarUser
                __typename
            }
            ...LatestContestResult
            __typename
        }
        fragment SimpleImage on PrintImageType {
            id
            filePath
            rotation
            imageHash
            imageWidth
            imageHeight
            __typename
        }""",
        "variables": {
            "categoryId": None,
            "competitionAwarded": False,
            "cursor": None,
            "featured": False,
            "hasMake": False,
            "limit": 36,
            "ordering": "-likes_count_30_days",
            "publishedDateLimitDays": 30
        }
    }

    if ordering:
        data['variables']['ordering'] = ordering

    response = requests.post(url, headers=headers, json=data)
    rj = response.json()

    return rj

def build_feed(rj, title, pagename):
    rss_out_json = {
       "version": "https://jsonfeed.org/version/1.1",
        "title": f"printables: {title}",
        "home_page_url": "https://www.printables.com/model",
        "feed_url": "https://dyn.tedder.me/rss/printables/{pagename}.json",
        "items": []
    }
    
    for i in rj['data']['models']['items']:
        #print(i['id'], i['name'], i['slug'], i['datePublished'], i['user']['publicUsername'])
        #print(i['image']['filePath'])
        model_url = f"https://www.printables.com/model/{i['id']}-{i['slug']}"
        model_img = f"https://media.printables.com/{i['image']['filePath']}"
        first_pub_date = datetime.datetime.fromisoformat(i['firstPublish'])
        rating = float(i['ratingAvg'])
        cats = []
        for c in i["category"]["path"]:
            cats.append(f"""<a href="https://www.printables.com/model?category={c['id']}">{c['name']}</a>""")
        cat_trail = " - ".join(cats)

        rss_out_json["items"].append( {
            "id": i['id'],
            "title": i['name'],
            "url": model_url,
            "image": model_img,
            "date_published": i['firstPublish'],
            "authors": {"name": i['user']['publicUsername'] },
            "content_html": f"""<h2>{i['name']}</h2>
    <img src="{model_img}" /><br />
    {i['likesCount']} likes, {i['downloadCount']} downloads, {rating:.2f} rating<br />
    first published {first_pub_date:%Y-%m-%d}<br />
    category: {cat_trail}
    """
        } )
        #break
    return rss_out_json

def save_and_upload_feed(rss_out_json, pagename):
    with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.json') as temp_file:
        json.dump(rss_out_json, temp_file, indent=2)
        print(f"RSS feed JSON written to {temp_file.name}")

    session = boto3.Session() #profile_name='pjnet')
    s3 = session.client('s3')
    bucket_name = 'dyn.tedder.me'
    object_name = f"rss/printables/{pagename}.json"

    s3.upload_file(temp_file.name, bucket_name, object_name, ExtraArgs={'ACL': 'public-read', 'ContentType': 'application/json'})
    print(f"File uploaded to s3://{bucket_name}/{object_name}")

pagesets = [
  ("-likes_count_30_days", "trending models", "trending"),
  ("-first_publish", "new models", "new"),
  ("-rating_avg", "top rated models", "top_rated"),
  ("-download_count_30_days", "top downloads", "top_downloads")
]

if __name__ == "__main__":
    for ordering, title, pagename in pagesets:
        rj = request_printables(ordering=ordering)
        #print(rj)
        with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.json') as temp_file:
            json.dump(rj, temp_file, indent=2)
            print(f"JSON written to {temp_file.name}")
        rss_out_json = build_feed(rj, title=title, pagename=pagename)
        save_and_upload_feed(rss_out_json, pagename=pagename)

