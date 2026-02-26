<template>
  <div class="app">
    <div class="header-container">

      <h5>Link mining <span>
                    <b-badge pill class="count" variant="dark">{{bookmarkCount}}</b-badge>
         </span>
      </h5>

    </div>
  <p class="info">Click Results to see related links</p>
    <div class="switch mt-3">
      <b-button-group>
        <b-button v-on:click="showSearchResults" class="switch-buttons" variant="dark">Results</b-button>
        <b-button v-on:click="openDashBoard" class="switch-buttons" variant="dark">Dashboard</b-button>
      </b-button-group>
    </div>

    <b-spinner v-if="loading" variant="dark" label="Loading..."></b-spinner>
    <div class="card" v-for="item in searchResults">
        <p> {{item.bookmark.title}}</p>
      <p> score: {{item.score}}</p>

      <b-button v-on:click="openLink(item.bookmark.url)" class="button" block variant="light">Open</b-button>
    </div>

  </div>
</template>

<script>
import BookmarkIndexer from "../services/BookmarkIndexer";
import {getHtml} from "../contentScript";
import stripHtml from "string-strip-html";
import nlp from "compromise";
import { mapState, mapGetters } from 'vuex'
import store from '../store'
export default {
  data: () => {
    return {
    loading:false
  }
  },
  methods: {
    openLink: (link) => {

       window.open(link, "_blank");
       return false
      // chrome.tabs.create({ url: link });
    },
    openDashBoard: () => {
      chrome.tabs.create({ url: "dashboard/dashboard.html" });
    },
    showSearchResults:  function()  {
        this.loading = true
    
      let content = getHtml((result)=> {
        var parsed = stripHtml(result).result
        console.log(parsed);
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

        store.dispatch('LOAD_SEARCH_LIST', {searchQuery: preporcessed.text()})
        this.loading = false
      });

    },
  },
  computed: {
    ...mapGetters([
      'bookmarkCount',
        'searchResults',
        "searchQuery"
    ]),
    ...mapState(['bookmarks'])
  },
  mounted: function () {
    store.dispatch('LOAD_BOOKMARK_LIST')
    store.commit("SET_SEARCH_LIST", {result:[]})
  }
};


</script>

<style lang="scss" scoped>
* {
  box-sizing: border-box;
}
.app {
  display: flex;
  flex-flow: column;
  align-content: center;
  align-items: center;
  justify-content: center;
  margin: auto;
  padding: 10px;
}
.switch {
  margin: auto;
  padding: 5px;
}
.switch-buttons {
  font-size: 15px;
}
.card {
  width:400px;
  min-height: 100px;
  background-color: #FF4500;
  border-radius: 8px;
  border-color: white;
  padding: 10px;
  margin: 10px;
}
.card > p {
  font-size: 12px;
  color: white;
}
.count {
  font-size: 12px;
}
.header-container {
}
.button {
  width: 200px;
}
.info {
  font-size: 10px;
  margin: auto;
}
</style>
