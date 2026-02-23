import * as React from 'react';
import AlphabetFlatList from "@yoonzm/react-native-alphabet-flat-list";
import { ListItem, SearchBar } from 'react-native-elements';
import ProgressLoader from 'rn-progress-loader';


const ICON_SIZE = 34;

import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  Pressable,
  Modal,
  FlatList,
  Image,
  Dimensions,
  UIManager

} from 'react-native';


// const file_name_list = {};
const all_data_list = [];
const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

const windowWidth = Dimensions.get('window').width;
const windowHeight = Dimensions.get('window').height;

const patt1 = /\./g;


export default class App extends React.Component {
  
  // const { value } = route.params;

  constructor() {
    super();
    this.state = { 
      isPasswordVisible: true,
      file_content : '',
      loading : false,
      file_name_list: {},
      data: [],
      selectedItems: [],
      error: null,
    }
  }

 state_change(index){
   this.setState({ isPasswordVisible : false });
 }

getSelected = contact => this.state.selectedItems.includes(contact);

// ----------------------- double click ------------------------ function = 1

selectItems = item => {
  console.log("==========>", item);
  this.setState({
    selectedItems: [
        ...this.state.selectedItems,
        item.uid
    ]
  })
  this.props.route.params.chooseItems.push(item);
  
};

//---------------------------- loading screen ------------------

loding_screen(){

  return (
    <View style={styles.container}>
      <ProgressLoader
              visible={true}
              isModal={true} isHUD={true}
              hudColor={"#E5E4E2"}
              color={"#00008B"} />
    </View>
  );

}


// ----------------------- single click ------------------------  function = 2

handleOnPress = (each_item, accessKey) => {
  
  if(this.state.selectedItems.length > 0){
    this.setState({
      selectedItems: this.state.selectedItems.filter(function(person) { 
        return person !== each_item.uid
    })
    });

    this.props.route.params.chooseItems = this.props.route.params.chooseItems.filter(function(person) { 
      return person.uid !== each_item.uid
    })
  }else{

      try{

        let file_type = each_item['file']['mimeType'].split('/')[0];

          if(file_type === 'image'){
            this.props.navigation.navigate('ShowFiles', each_item);
          }else if(file_type === 'application'){
            alert(" Extention not avilable ...");
          }else if(file_type === 'text'){
            alert(" Extention not avilable ...");
          }else if(file_type === 'video'){
            this.props.navigation.navigate('VideoFiles', each_item);
          }else{
            alert(" Extention not avilable ...");
          }

      }catch{
        this.each_folder_access(each_item, accessKey)
      }

  }
  
};

// ----------------------------------------------- renderViewPart   function = 3

 renderViewPart = (item, accessKey, selected) => {


  return <TouchableOpacity style={styles.item_st} onPress={() => this.handleOnPress(item, accessKey)} onLongPress={() => this.selectItems(item)} >
            <View style={styles.item}>
              <View style={{ height: '100%', width: '19%', alignItems: 'center', justifyContent: 'center'}} >
                {item.name.match(patt1) === null ? <Image source={{ uri: 'asset:/folder.png' }} style={styles.folderIcon} /> : 
                  item.name.slice(-3) === 'pdf' ? 
                    <Image source={{ uri: 'asset:/pdf.png' }} style={styles.pdfIcon} /> :
                  (item.name.slice(-3) === 'jpg' || item.name.slice(-3) === 'peg' || item.name.slice(-3) === 'png' ) ?
                    <Image source = {{ uri:item['@microsoft.graph.downloadUrl'] }} style={styles.imageIcon} /> :
                  item.name.slice(-3) === 'mp4' ?
                    <Image source = {{ uri: 'asset:/video.png' }} style={styles.videoIcon} /> :
                  item.name.slice(-3) === 'txt' ?
                    <Image source = {{ uri: 'asset:/text_icon.png' }} style={styles.textIcon} /> : 
                    <Image source = {{ uri: 'asset:/unknown.png' }} style={styles.textIcon}  /> }
              </View>
              {item.name.match(patt1) === null ?
                <View style={{  height: '100%', width: '80%', marginTop: '2%'}} >
                  <Text style={styles.eachItem} >{item.name}</Text>
                  <Text style={styles.dateText} >{this.numberOfItems(item)} |</Text>
                  <Text style={styles.numberOf} >{this.dateAlignment(item)}</Text>
                </View>
                :
                <View style={{ height: '100%', width: '80%', marginTop: '2%'}} >
                  <Text style={styles.eachItem} >{item.name}</Text>
                  <Text style={styles.singleFileDate} >{this.dateAlignment(item)}</Text>
                </View>
              }
            </View>
            {selected && <View style={styles.overlay} />}
          </TouchableOpacity>
  
}

// ----------------------------------------------- renderHeader   function = 4


 renderHeader = (accessKey) => {

  let iconView = Math.round(windowHeight) - 750;


  return (
    // <TouchableOpacity onPress={() => this.props.navigation.navigate('SearchFiles', {'value' : all_data_list})} ><View style={styles.searchBar}  >

    <TouchableOpacity style={{ height: 55}} onPress={() => this.props.navigation.navigate('SearchSingleFile', {'access' : accessKey})} >
      <View style={styles.searchBar}  >
              <Image
                source = {{ uri: 'asset:/search_blue.png' }}
                style={styles.searchIcon}
              />
              <Text style={{ fontSize: 18, marginLeft: '18%', marginTop: '-10%'}} >Search</Text>
      </View>
    </TouchableOpacity>
    
  );
};

// ----------------------------------------------- dateAlignment   function = 5

dateAlignment(item){
  var mydate = new Date(item.fileSystemInfo.createdDateTime);
  mydate = mydate.toDateString();
  mydate = mydate.split(' ');
  return mydate[2] + ' ' + mydate[1] + ' ' + mydate[3];
  
};

// ----------------------------------------------- number of items   function = 6

numberOfItems(folder_res){

  return folder_res.folder.childCount + ' ' + 'items';

}

// ---------------------------------------------- deselect items   function = 7

deSelectItems = () => this.setState({ selectedItems : []});


// ---------------------------------------------- each folder  function = 8


async each_folder_access(item, access_key){

  var _urlFiles = `https://graph.microsoft.com/v1.0/me/drive/items/${item.id}/children`;
    
    let response_data = await fetch(_urlFiles, {
  
          method: 'GET',
          headers: new Headers({
              'Authorization': 'Bearer '+ access_key,
              'Accept': 'application/json'
            }),
          }).then(
          ).catch(function(err) {
          console.log('Fetch Error :-S', err);
        });
    
    let each_folder_list = await response_data.json();

    // each_folder_list['accessToken'] = access_key;

    if (each_folder_list){
      if(this.props.route.params.folderNavigation.length > 0){
        this.props.route.params.folderNavigation = [];

      }
      this.props.route.params.folderNavigation.push(each_folder_list);
      // // let code_id = each_folder_list["@odata.context"];
      // // let code_id2 = String(code_id).split('/').splice(-2)[0];
      // // let pattern = /[A-Z\d%]+/m;
      // // this.props.route.params.cfolderId.push(code_id2.match(pattern)[0])
      this.props.route.params.cfolderId.push(item.id)
      this.props.navigation.navigate('FolderInsideList', this.props.route.params);
    }


}

// -------------------------------------------- Render function = 9

    
  render() {

    const all_files = this.props.route.params.value;
    const accessKey = this.props.route.params.value.accessToken;


    var patt1 = /\./g;

    for (let i = 0; i < letters.length; i++) {
      let coll = [];

      for (let j = 0; j < all_files.length; j++){
        if (letters[i] == all_files[j].name[0].toUpperCase()){
          coll.push(all_files[j]);
        }
        if (letters[i].toUpperCase() == 'A'){
          all_files[j].uid = j;
          all_data_list.push(all_files[j]);
        }

      }
      if (coll.length > 0){
        this.state.file_name_list[letters[i]] = coll;
      }

    }
    
// -------------------------------------------- Alphabetflatlist

  return (
    <View style={styles.container} >
    {/* <Loader loading={this.state.loading} /> */}
    {this.state.isPasswordVisible ?
        <Pressable onPress={this.deSelectItems} style={{flex: 1, padding: 5}}>
          <AlphabetFlatList
              data={this.state.file_name_list}
              renderItem={({item}) => this.renderViewPart(item, accessKey, this.getSelected(item.uid))}   
              keyExtractor={(item, index) => item.uid}
              itemHeight={4}
              headerHeight={4}
              ListHeaderComponent={this.renderHeader(accessKey)}
            />  
        </Pressable>
            : this.after_login()}

        </View>
    
  )
  
  }

}


// --------------------------------------------------- css part --------------------------------------------------


const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  item_st: {
    backgroundColor: "white",
    overflow: 'hidden',
  },
  item: {
    height: 80, 
    // alignItems : 'flex-start',
    flexDirection: 'row',
    justifyContent: 'space-between',
    padding: 3
  },
  title: {
    fontSize: 12,
  },
  folder_name: {
    top: -40,
    fontSize: 22,
    left: 100
  },
  folderIcon: {
    height: '60%', width: '60%'
  },
  pdfIcon:{
    height: '65%', width: '53%'
  },
  textIcon:{
    height: '70%', width: '75%'
  },
  videoIcon:{
    height: '50%', width: '75%'
  },
  imageIcon:{
    height: '70%', width: '75%', 
  },
  
  imageView:{
    marginTop: 20,
    marginLeft: 10,
    width: 60, 
    height: 60,
    // backgroundColor : '#800000',
    alignItems:'center',
  },
  eachItem: {
    marginTop: 2,
    marginLeft: 10, 
    fontSize: 18,
  },
  dateText:{
    marginLeft: 10,
    opacity: 0.3
  },
  singleFileDate: {
    marginLeft: 10,
    opacity: 0.3
  },
  numberOf: {
    marginTop: -18,
    marginLeft: 70,
    opacity: 0.3
  },
  textView: {
    width: windowWidth,
    height: 60,
    // backgroundColor : '#ADD8E6',
    marginTop: -60,
    left : 70,
  },
  searchBar:{
    backgroundColor: '#DCDCDC',
    width: '98%',
    height: '95%'
  },
  searchText:{
    opacity: 0.3,
    fontSize: 20,
  },
  searchIcon: {
    width: '15%', height: '97%', marginTop: '0.5%', marginLeft: '1%'
    
  },
  overlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
    backgroundColor: 'rgba(77, 83, 69, 0.4)',
    borderWidth: 1
  },
})
