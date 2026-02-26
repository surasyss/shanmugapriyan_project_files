import Vue from 'vue'
import Vuex from 'vuex'
import BookmarkIndexer from "../services/BookmarkIndexer";
import moment from "moment";
import sha1 from 'sha1';
import DBHelper from '../services/DBHelper'

Vue.use(Vuex)

class BookmarkModel {
  parsedStr = '';
  isParsed = false;
  status = "In queue"
  constructor(val) {
    this.bookmark = val;
    this.id = sha1(val.url);
  }
}
const store = new Vuex.Store({
  state: {
    bookmarks: [],
    results:[],
    searchQuery: ""
  },
  actions: {
    LOAD_BOOKMARK_LIST: function ({ commit , state}) {
      const bookMarkList = [];
      const fetchBookmark = (bookmarks) => {
        console.log("called fetchbookmark")
        for (var i = 0; i < bookmarks.length; i++) {
          var bookmark = bookmarks[i];
          if (bookmark.url) {
            let bookmarkobj = new BookmarkModel(bookmark);
            bookMarkList.push(bookmarkobj);
          }
          if (bookmark.children) {
            fetchBookmark(bookmark.children);
          }
          else {
            continue;
          }

        }
        commit('SET_BOOKMARK_LIST', { list: bookMarkList })
      }
      chrome.bookmarks.getTree((tree) => {
          if (state.bookmarks.length == 0){
            var result = fetchBookmark(tree);
          }
      });
    },
    LOAD_SEARCH_LIST: function ({ commit, state }, {searchQuery}) {
      const instance = new BookmarkIndexer();
      let dbHelper = new DBHelper();
      dbHelper.getAllBookmarks().then((data)=> {
        let index = instance.addAllBookmarksToIndex(data)
        const results = instance.searchIndex(index, state.bookmarks, searchQuery);
        commit('SET_SEARCH_LIST',{results})
      })
    },
    ADD_BOOKMARK: function ({ commit }, {bookmark}) {
      commit('CREATE_BOOKMARK', { bookmark })
      const api = new BookMarkApi(state.bookmarks);
      api.start((data) => {
        console.log("resulted",data)
        const {rawText, id} = data;
        commit('UPDATE_BOOKMARK', { rawText, id })
        commit('ADD_DATA_TO_INDEX', { rawText, id })
      })
    },
    ADD_SEARCH_QUERY: function ({ commit }, {query}) {
      commit('ADD_SEARCH', { query })
    },
    CLEAR_DATA: function ({ commit }) {
      commit('CLEAR_ALL')
    },
  },
  mutations: {

    SET_BOOKMARK_LIST: (state, { list }) => {
      state.bookmarks = list
    },
    SET_SEARCH_LIST: (state, { results }) => {
      state.results = results
    },
    ADD_SEARCH: (state, { query }) => {
      state.searchQuery = query
    },
    CLEAR_ALL: (state) => {
      state.searchQuery = ""
      state.bookmarks = []
      state.bookmarkIndexData = ""
      state.results = []
    },

    UPDATE_BOOKMARK: (state, { rawText, id}) => {
      console.log("update bookmarks",state.bookmarks);
      let idx = state.bookmarks.findIndex( x => x.id === id );

      let currentBookmark = { ...state.bookmarks[idx], parsedStr:rawText, isParsed: true }
      console.log("current",id,idx)
      state.bookmarks.splice(idx, 1, currentBookmark)
    },
    CREATE_BOOKMARK:  (state, { bookmark }) => {
      let bookmarkobj = new BookmarkModel(bookmark);
      state.bookmarks.push(bookmarkobj)
    },
  },
  getters: {
    bookmarkCount: state => {
      return state.bookmarks.length
    },
    bookmarkItems: state => {
      return state.bookmarks.map(function (item) {
        let dateAdded = moment(item.bookmark.dateAdded).format('MM-DD-YYYY hh:ss A')
        let dateGroupModified = moment(item.bookmark.dateGroupModified).format('MM-DD-YYYY hh:ss A')
        return {...item,title:item.bookmark.title, url:item.bookmark.url, dateAdded:dateAdded,Modified:dateGroupModified}
      });

    },
    searchResults:state => {
      return state.results
    },
    searchQuery: state => {
      return state.searchQuery
    },
    indexCompletedCount: state => {
      return state.bookmarks.filter((obj) => obj.isParsed).length
    }
  },

})

export default store
