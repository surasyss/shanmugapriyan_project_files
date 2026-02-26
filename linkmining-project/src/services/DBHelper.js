import { openDB, DBSchema } from 'idb';
import {v4 as uuidv4} from "uuid";


const BOOKMARK_STORE = 'bookmarkStore';
const MODEL_STORE = 'modelStore';
const DB_NAME = 'Linkmining';
const ELASTIC_LUNR_MODEL = 'elastic_lunar';

const database = openDB(DB_NAME, 1, {
    upgrade(db) {
        const bookmarkStore = db.createObjectStore(BOOKMARK_STORE, {
            keyPath: 'id',
        });
        db.createObjectStore(MODEL_STORE);
        bookmarkStore.createIndex('id', 'id');
    }
});

export default class IndexDBHelper {
    constructor(props) {
    }

    async openDB() {
        // this.database = await openDB(DB_NAME, 1, {
        //     upgrade(db) {
        //         const bookmarkStore = db.createObjectStore(BOOKMARK_STORE, {
        //             keyPath: 'id',
        //         });
        //         // const modelStore = db.createObjectStore('modelStore', {
        //         //     keyPath: 'id',
        //         // });
        //         bookmarkStore.createIndex('id', 'id');
        //         // modelStore.createIndex('id', 'id');
        //     },
        // });
    }

    async get(key) {
        return (await database).get(BOOKMARK_STORE, key);
    }
    async set(key, val) {
        return (await database).put(BOOKMARK_STORE, val, key);
    }
    async update(key, val) {
        // let current = await this.get(key);
        // let toUpdate =  {...current, ...val}
        // console.log("toUpdate", toUpdate)
        // return (await database).put('bookmarkStore', current, key);


        let current = await this.get(key);
        database.then((db) => {
            const transaction = db.transaction([BOOKMARK_STORE], 'readwrite');
            const objectStore = transaction.objectStore(BOOKMARK_STORE);
            let toUpdate =  {...current, ...val}

            objectStore.put(toUpdate)
            return transaction.complete
        })
            .then(() => {
                console.log('Transaction complete')
            })
            .catch((err) => {
                console.log('Transaction failed',err)
            })

    }
    async delete(key) {
        return (await database).delete(BOOKMARK_STORE, key);
    }
    async clear() {
        return (await database).clear(BOOKMARK_STORE);
    }
    async getAllBookmarks() {
        const data = (await database).getAll(BOOKMARK_STORE);
        return data
    }
    async insertBookmarks(bookmarks) {
        const tx = (await database).transaction(BOOKMARK_STORE, 'readwrite');
        return await Promise.all(bookmarks.map((bookmark)=>{
            return tx.store.add({...bookmark})
        }))
    }

    async insert(key, value) {
        let current = await this.get(key);
        if (current !== undefined) {
            console.log("already parsed")
            return
        }

        const tx = (await database).transaction(BOOKMARK_STORE, 'readwrite');
        return await tx.store.add({...value})
    }
    async getModelData() {
        let data =  (await database).get(MODEL_STORE,ELASTIC_LUNR_MODEL);
        return data
    }
    async setModelData(val) {

        const tx = (await database).transaction(MODEL_STORE, 'readwrite');
        const store = tx.objectStore(MODEL_STORE);
        await store.put(val, ELASTIC_LUNR_MODEL);
        return await tx.done;

        // return database.then((db) => {
        //     const transaction = db.transaction(MODEL_STORE, 'readwrite');
        //     const objectStore = transaction.objectStore(MODEL_STORE);
        //     objectStore.put(val, ELASTIC_LUNR_MODEL);
        //     return transaction.complete
        // })
        


        // return (await database).put(MODEL_STORE, "val", ELASTIC_LUNR_MODEL);

    }
}
