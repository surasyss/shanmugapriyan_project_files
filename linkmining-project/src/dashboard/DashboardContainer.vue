<template>
    <b-container fluid>
      <b-row class="mt-5">
        <b-col lg="3" class="">
          <div class="mb-4">
            <h5>Link mining</h5>
            <div class="input-group">
              <b-form-input
                  v-model="filter"
                  type="search"
                  id="filterInput"
                  placeholder="Search Bookmark"
              ></b-form-input>

            </div>
          </div>
          <div class="mb-4">
            <div class="small mb-3">Jobs</div>
            <ul class="nav flex-column nav-pills">
              <li class="nav-item"><a href="#" class="themeTextColor nav-link active themeBackground"><i
                  class="fa fa-fw fa-line-chart mr-2"></i>Bookmarks</a></li>
              <li class="nav-item"><a href="#" class="themeTextColor nav-link"><i
                  class="fa fa-fw fa-calendar-o mr-2"></i>Export Index file</a></li>
            </ul>
          </div>
          <div class="mb-4">
            <div class="small mb-3">Status</div>
            <ul class="nav flex-column nav-pills">
              <li class="nav-item"><a href="#" class="d-flex themeTextColor nav-link"><i
                  class="fa fa-fw fa-star-o align-self-center mr-2"></i>Total Bookmarks<span
                  class="ml-auto align-self-center badge badge-secondary badge-pill">{{bookmarkCount}}</span></a>
              </li>
              <li class="nav-item"><a href="#" class="d-flex  themeTextColor nav-link"><i
                  class="fa fa-fw fa-star-o align-self-center mr-2"></i>Indexing Completed<span
                  class="ml-auto align-self-center badge badge-secondary badge-pill">{{indexCompletedCount}}</span></a></li>
            </ul>
          </div>
        </b-col>
        <b-col lg-9 class="">
          <div class="d-flex flex-column flex-md-row mb-3 mb-md-0 justify-content-center" >
            <div role="toolbar" class="btn-toolbar">
              <div role="group" class="mr-auto mr-md-2 btn-group">
                <b-button  v-on:click="startIndexingTapped" variant="dark" class="align-self-center" id="tooltipShowList"> Start Indexing </b-button>
                <b-button  v-on:click="clearIndexDataTapped" variant="dark" class="align-self-center" id=""> Clear Index Data </b-button>

              </div>
            </div>
          </div>
          <div class="mt-2 mb-3 Card_custom-card--border_5wJKy card">

              <div>

                <b-table striped hover :items=bookmarkItems :fields="fields"
                         id="my-table"
                         :per-page="perPage"
                         :filter="filter"
                         :total-rows="bookmarkCount"
                         :current-page="currentPage"
                         small
                         @filtered="onFiltered"
                >
                  <template #cell(title)="data">
                    <span class="titleColor">{{ data.value }}</span>
                  </template>
                  <template #cell(url)="data">
                    <a class="urlStyle" :href="data.value" target="_blank">{{ data.value }}</a>
                  </template>
                  <template #cell(dateAdded)="data">
                    <span class="titleColor">{{ data.value }}</span>
                  </template>
                  <template #head()="data">
                    <span class="tableHeader">{{ data.label.toUpperCase() }}</span>
                  </template>
                </b-table>

                <b-pagination
                    v-model="currentPage"
                    :total-rows="totalRows"
                    :per-page="perPage"
                    aria-controls="my-table"
                ></b-pagination>

              </div>
            </div>
        </b-col>
      </b-row>
    </b-container>

</template>

<script>
import {mapGetters, mapState} from "vuex";
import store from "../store";
import DBHelper from "../services/DBHelper";
import BookMarkApi from "../services/NetworkHelper";
import BookmarkIndexer from "../services/BookmarkIndexer";

export default {
  name: "DashboardContainer",
  data() {
    return {
      perPage: 10,
      currentPage: 1,
      filter: null,
      totalRows: 1,
      fields: [
        {
          key: 'title',
          sortable: true
        },
        {
          key:'url',
          sortable: false
        },
        {
          key: 'dateAdded',
          sortable: true
        },
        {
          
        }
      ],
    }
    },
  computed: {
    ...mapGetters([
      'bookmarkCount',
      'bookmarkItems',
      'searchResults',
      "searchQuery",
        "indexCompletedCount"
    ]),
    ...mapState(['bookmarks']),
  },
  methods: {
    startIndexingTapped() {

let dbHelper = new DBHelper();

  const api = new BookMarkApi(this.bookmarkItems);
  api.start((data) => {
    const {rawText, id} = data;
   store.commit('UPDATE_BOOKMARK', {rawText, id})
   if (rawText == null) {
     return
   }
    let idx = this.bookmarkItems.findIndex( x => x.id === id );
    let currentData = this.bookmarkItems[idx];
    let modifiedData = { parsedStr:rawText,
      isParsed:true, id, ...currentData }
    dbHelper.insert(id,modifiedData)

  }, () => {

    console.log("completed queue and all done")
       

  })

    },
  onFiltered(filteredItems) {
    this.totalRows = filteredItems.length
    this.currentPage = 1
  },
    async clearIndexDataTapped() {
      // store.dispatch('CLEAR_DATA')
      console.log(this.bookmarkItems)

    }
  },
  mounted: function () {
          store.dispatch('LOAD_BOOKMARK_LIST')
            // let indexer = new BookmarkIndexer();
            // indexer.createInitialIndex();

  }
}
</script>

<style scoped>
.themeBackground {
  background-color: #FF4500 !important;
}
.themeTextColor  {
  color: black !important;
}
a.active  {
  color: white !important;
}
.titleColor {
  color:  black !important;
  font-size: 13px;
}
.urlStyle {
  color:  dodgerblue !important;
  font-size: 13px;
}
.tableHeader {
  color: black !important;
  font-size: 13px;
}

</style>
