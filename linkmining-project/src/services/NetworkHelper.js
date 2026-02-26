import stripHtml from "string-strip-html";
import nlp from 'compromise'
import DBHelper from "../services/DBHelper";
const Queue = require('queue');
const axios = require('axios');
import sha1 from 'sha1';
import BookmarkIndexer from "../services/BookmarkIndexer";

export default class BookMarkApi {

    queue = Queue();
    CUNCURRENCY = 5;
    dbHelper = new DBHelper();
    indexer = new BookmarkIndexer()

    constructor(data) {
        this.bookMarkList = data;
        this.queue.concurrency = this.CUNCURRENCY;
    }
    start =  async (completion, finished) => {
        let filtered = this.bookMarkList.filter((obj) => !obj.isParsed)

        for (let bookmarkObj of filtered) {
            const newvalue = bookmarkObj;
            console.log(newvalue.url);
            let urlHash = sha1(newvalue.url);
            let dataForId = await this.dbHelper.get(urlHash);
                    
                if (dataForId !== undefined) {
                    console.log("exists already",dataForId)
                    completion({id:urlHash,rawText:null})
                     continue;
                }
            this.queue.push((callback) => {
                
                const data = this.fetchDataFromUrl(newvalue.url).then((parsedResult) => {
                    let modifiedData = { ...newvalue,parsedStr:parsedResult,
                        isParsed:true,  id:urlHash }
                        callback(null, { rawText:parsedResult, id:urlHash});

                }).catch((err) => {
                    console.log(err)
                })
            })
        }

        this.queue.on('success', function (result, job) {
            completion(result)
            console.log('job finished processing:', job.toString().replace(/\n/g, ''))
        });
        this.queue.start(function (err) {
            if (err) throw err
            console.log('all done:')
            finished()
        })
    }
    fetchDataFromUrl = async (url) => {
        console.log(url);
        const options = {
            method: 'GET',
            headers: {
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Origin': '*',
            },
            url
        };
        try {
            const response = await axios(options)
            var html = response.data
            var parsed = stripHtml(html).result
            var doc = nlp(parsed)
            doc.normalize({
                whitespace: true,
                case: true,
                punctuation: true,
                unicode: true,
                contractions: true,
                acronyms: true,
                parentheses: true,
                possessives: true,
                plurals: true,
                verbs: true,
                honorifics: true
            })
            // html = html.replace(/(<([^>]+)>)/ig, '');
            // html = html.replace(/<script[^>]*>(?:(?!<\/script>)[^])*<\/script>/g, "")
            // console.log('api response',html)
            // let preporcessed = doc.topics().concat(doc.verbs()).concat(doc.adverbs()).concat(doc.nouns()).concat(doc.nouns()).concat(doc.nouns().adjectives()).unique()
            return doc.text('normal')
        } catch (err) {
            console.log(err); // TypeError: failed to fetch
        }


    }

}