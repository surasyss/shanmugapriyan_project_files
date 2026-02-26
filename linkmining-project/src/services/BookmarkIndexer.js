
const elasticlunr = require('elasticlunr');
import DBHelper from "../services/DBHelper";

export default class BookmarkIndexer {

    addAllBookmarksToIndex = (bookmarks) => {
        var index = elasticlunr(function () {
            this.addField('title')
            this.addField('body')
            this.setRef('id');
            this.saveDocument(false);
        });
        bookmarks.forEach((bookmark) => {
            index.addDoc({
                "id": bookmark.id,
                "title": bookmark.bookmark.title,
                "body": bookmark.parsedStr
                });
        });
        return index;
    }
    searchIndex = (index, bookmarks,query) => {
        let searchResults = index.search(query, {
            fields: {
                title: {boost: 2},
                body: {boost: 1}
            },
            bool: "OR",
            expand: true
        });

        // let filteredBookMarks = bookmarks.filter(o1 => searchResults.some(o2 => o1.id === o2.ref));
        var mergedResult = searchResults.map((result)=> {
            var haveEqualId = (bookmark) => bookmark.id === result.ref
            var userWithEqualId= bookmarks.find(haveEqualId)
            return Object.assign({}, result, userWithEqualId)
        })
        console.log("search result",mergedResult, index)
        return mergedResult.sort((a,b) => b.score-a.score)
    }
    getIndex = (indexString) => {
        if (indexString == null || indexString === "" || indexString === undefined) return null;
        let indexDump = JSON.parse(indexString);
        let index = elasticlunr.Index.load(indexDump)
        return index
    }
    addDocToIndex = (indexString, bookmark) => {
        var index = this.getIndex(indexString)
        if (index == null) {
            index = elasticlunr(function () {
                this.addField('title')
                this.addField('body')
                this.setRef('id');
                this.saveDocument(false);

            });
        }
        index.addDoc(
             {
                "id": bookmark.id,
                "title": bookmark.bookmark.title,
                "body": bookmark.parsedStr
            }
        );
       
        return index
    }

    createInitialIndex = async () => {
        let dbHelper = new DBHelper();

        let storedindexString = await dbHelper.getModelData();
        var index = this.getIndex(storedindexString)
        if (index == null) {
            index = elasticlunr(function () {
                this.addField('title')
                this.addField('body')
                this.setRef('id');
                this.saveDocument(false);
            });
            let indexString = JSON.stringify(index)
            dbHelper.setModelData(indexString).then((result) => {
            });
        }
        return;
        
    }
}