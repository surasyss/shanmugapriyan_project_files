import {getHtml} from "./contentScript";

global.browser = require('webextension-polyfill')
import store from "./store";
import stripHtml from "string-strip-html";
import nlp from "compromise";

chrome.bookmarks.onCreated.addListener((id, bookmark) => {
    store.dispatch("ADD_BOOKMARK", { bookmark })
})
// chrome.tabs.onUpdated.addListener((tabId,changeInfo, Tab) => {
//
//     var queryInfo = {
//         active: true,
//         currentWindow: true
//     };
//     // alert(changeInfo.url)
//     if (changeInfo.url != undefined) {
//         chrome.tabs.query(queryInfo, (tabs) => {
//             let currentTab = tabs[0];
//             if (currentTab.id === tabId) {
//                 getSearchQuery()
//             }
//         });
//     }
//
//
// })
// chrome.tabs.onActivated.addListener((activeInfo) => {
//     getSearchQuery()
// })

function getSearchQuery() {
    let content = getHtml((result)=> {
        var parsed = stripHtml(result).result
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
          let preporcessed = doc.topics().concat(doc.verbs()).concat(doc.nouns()).concat(doc.nouns().adjectives()).unique()
        //
        //   var items = ['covid 19', 'type c'];
        //   var item = items[Math.floor(Math.random() * items.length)];
        // store.dispatch('ADD_SEARCH_QUERY', {query: doc.topics().text()})
    });
}