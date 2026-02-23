import 'react-native-gesture-handler';
import React, { Component, useState, useEffect } from 'react';
import { Platform, StyleSheet, Image, Text, View, Button, TouchableOpacity, FlatList, ActivityIndicator } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { CommonActions } from '@react-navigation/native';
import SplashScreen from 'react-native-splash-screen';
import Home from './webscreen/HomeScreen.js';
import Modal from 'react-native-modal';
import MicrosoftLogin from './webscreen/MicrosoftLoginPage.js';
import OneDriveFiles from './webscreen/OneDriveItems.js';
import FolderInside from './webscreen/FolderInside.js';
import ShowFile from './webscreen/ShowFile.js';
import VideoFile from './webscreen/VideoFile.js';
import NormalVideoExample from './webscreen/NormalVplayer.js';
// import CustomMenu from './webscreen/CustomMenu';
import Icon from 'react-native-vector-icons/dist/FontAwesome';
import AlphabetFlatList from "@yoonzm/react-native-alphabet-flat-list";
// import SearchFiles from './webscreen/SearchFiles.js';
import SearchSingleFile from './webscreen/SearchSingleFile.js';
import Loader from './webscreen/Loder.js';
import { Dimensions } from 'react-native';



const windowWidth = Dimensions.get('window').width;
const windowHeight = Dimensions.get('window').height;
var count = 0;


const Stack = createStackNavigator();

function LogoTitle() {
  return (
    <View style={styles.headerView}><Text style={styles.welcomeHeader} > Onedrive </Text></View>
  );
}



const App  = () => {

  const [visible, setVisible] = useState(false);
  const [li_item, setLi_item] = useState([]);
  const [param1, setParam1] = useState({});
  const [model_view, setmodel_view] = useState(false);
  const [delete_model, setDelete_model] = useState(false);
  const [loader, setLoder] = useState(false);
  const [navigate_c, setNavigate] = useState({});
  const [yes, setYes] = useState(false);

    React.useEffect(() => {
      SplashScreen.hide();
    });

    copy_method = (route_2, navigation_2, params_2) => {

      if (param1.chooseItems.length > 0) {

        setmodel_view(false);

        navigation_2.reset({
          index: 0,
          routes: [{ name: 'OneDriveFiles', params: param1}],
        });
      }else{
        alert(" No item selected ....");
      }

    };

    async function paste_method(navigation_4){

      if (param1.chooseItems.length > 0) {
         
        setLoder(true);
        let copy_itemId = param1.chooseItems[-1].id;
      
          if (folder_id.length === 0){

            var driveItem_query = {
              name: "copy_"+copy_item_id[0].name,
            };

          }else{
            var driveItem_query = {
              parentReference: {
                // parant folder id
                id: folder_id[0],
              },
              name: "copy_"+copy_item_id[0].name,
            };
          }
        

        let _urlFiles = `https://graph.microsoft.com/v1.0/me/drive/items/${copy_itemId}/copy`;
          
        let response_data = await fetch(_urlFiles, {
              method: 'POST',
              headers: new Headers({
                  'Authorization': 'Bearer '+ param1.value.accessToken, 
                  'Accept': 'application/json',
                  'Content-Type': 'application/json'
                }),
              body: JSON.stringify(driveItem_query),
              }).then( console.log("==== success ====")
              ).catch(function(err) {
              console.log('Fetch Error :-S', err);
            });

        console.log("------------- copy completed ----------")

        if (folder_id.length !== 0){
          
          let _urlFiles2 = `https://graph.microsoft.com/v1.0/me/drive/items/${param1.cfolderId[-1]}/children`;
  
          let response_data2 = await fetch(_urlFiles2, {
        
                method: 'GET',
                headers: new Headers({
                    'Authorization': 'Bearer '+ param1.value.accessToken, 
                    'Accept': 'application/json'
                  }),
                }).then(
                ).catch(function(err) {
                console.log('Fetch Error :-S', err);
              });

          let each_folder_list2 = await response_data2.json();
          if (each_folder_list2){
            param1.folderNavigation = [];
            param1.cfolderId = [];
            param1.chooseItems = [];
            param1.folderNavigation.push(each_folder_list2);
            navigation_4.dispatch(
              CommonActions.navigate({
                name: 'FolderInside',
                params: param1
              })
            );
          }

        }

          if(response_data.status == 202){
            console.log(" Item copied successfully ...");
          }else{
            console.log("-------->", response_data);
            alert("Server issues item not copied ..."); 
          }
        setLoder(false);
        setmodel_view(false);
        
      }else{
          setmodel_view(false);
          alert(" No item selected ....");
      }
          
    }

    cancel_method = (name, navigation_5) => { 

      console.log("----------------->", param1.chooseItems.slice(-1));

      // for(let x =0 ; x < param1.chooseItems.length ; x++){

      //   console.log("---------->", param1.chooseItems[x]);

      // };
      
      
    };

    function onpress_three_dot(){
      // setVisible(true);
      setmodel_view(true);
    };

    function out_side_press(){
      // setVisible(false);
      setmodel_view(false);
    }


    async function delete_method(con){
    

      if (con) {

        let delete_item_id = param1.chooseItems;
        setLoder(true);
        let _urlFiles2 = "https://graph.microsoft.com/v1.0/me/drive/root/children";

        for (let i = 0; i < delete_item_id.length; i++) {
          let link_part = delete_item_id[i].id;
          let _urlFiles = `https://graph.microsoft.com/v1.0/me/drive/items/${link_part}`;        
          let response_data = await fetch(_urlFiles, {
                method: 'DELETE',
                headers: new Headers({
                    'Authorization': 'Bearer '+ param1.value.accessToken,
                    'Accept': 'application/json'
                  }),
                }).then(function(res) {
                  console.log('Success :-S', res);
                }
                ).catch(function(err) {
                console.log('Fetch Error :-S', err);
              });
        }
  
      // -----------------------------------------------------------------------------------
  
        let res_data = await fetch(_urlFiles2, {
      
              method: 'GET',
              headers: new Headers({
                  'Authorization': 'Bearer '+ param1.value.accessToken, 
                  'Accept': 'application/json'
                }),
              }).then(
              ).catch(function(err) {
              console.log('Fetch Error :-S', err);
            });
        
        let files_list = await res_data.json();
        files_list.value.accessToken = param1.value.accessToken;
        files_list.chooseItems = [];
        files_list.cfolderId = [];
        files_list.folderNavigation = [];
        // setParam1(files_list);
  
        navigate_c.reset({
          index: 0,
          routes: [{ name: 'OneDriveFiles', params: files_list}],
        });
        setLoder(false);
        alert(" sucessfully deleted ...");
        setmodel_view(false);

      }else{
        param1.chooseItems = [];
        setmodel_view(false);
        navigate_c.reset({
          index: 0,
          routes: [{ name: 'OneDriveFiles', params: param1}],
        });
      }
  
      
    }

    function call_delete_method(con){

      if (con === 'OK'){

        setDelete_model(false);
        delete_method(true);

      }else{

        setDelete_model(false);
        delete_method(false);
      }

       
    }
    

    
    HomeScreen = (route, navigation) => { 
      
      // try{
          
      //   if (route.params.value.length > 5){
      //      setParam1(route.params);
      //      setNavigate(navigation);
      //   }

      // }catch{
      //   console.log("");
      // }

      useEffect(() => {
        // console.log(`You clicked times`,"----?", );
        setParam1(route.params);
        setNavigate(navigation);
      }, [route.params]);
      
      
      if (route.name === 'OneDriveFiles') {

        return(
          <View style={{ flex: 1 }}>
            <Loader loading={loader} />
            <TouchableOpacity onPress={() => onpress_three_dot()}>
                <Image
                  style={{ height: 20, width: 20, marginRight: 20, marginTop: 8}}
                  source = {{ uri: 'asset:/3dot.png' }}
                />
              </TouchableOpacity>

              <Modal animationIn="slideInUp" animationOut="slideOutDown"  
              isVisible={delete_model} style={{backgroundColor: "transparent", maxHeight: '100%'}}>
                <View style={styles.deleteModel} >
                  <Text style={styles.deleteModelText}>
                    Sure you want delete selected item ?</Text>
                  <TouchableOpacity style={{ backgroundColor: "#63D555", alignSelf: 'flex-start', marginLeft: '20%', marginTop: '10%' }} 
                    onPress={() => call_delete_method('OK')}>
                    <Text style={{ paddingTop : '3%', paddingLeft: '10%', paddingRight: '10%', paddingBottom: '3%'}}>
                      Yes</Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={{ backgroundColor: "#ec1313", alignSelf: 'flex-end', marginRight: '20%', marginTop: '-10.2%' }} 
                   onPress={() => call_delete_method('NO')} >
                    <Text style={{ paddingTop : '3%', paddingLeft: '11%', paddingRight: '11%', paddingBottom: '3%'}}>
                      No</Text>
                  </TouchableOpacity>
                </View>
              </Modal>
              
              {model_view === true ?
              <Modal animationType="slide" isVisible={true}  onBackdropPress={() => out_side_press()}
                  animationIn="fadeInDown"
                  animationOut="fadeOutDown"
                  style={{backgroundColor:'white', maxHeight: '100%', width: windowWidth, overflow: "hidden", backgroundColor: "transparent"}}>
                <View style={styles.content}>
                  <TouchableOpacity style={styles.cpdc} onPress={()=> copy_method(route, navigation, route.params)}>
                      <Image
                      style={{ height: 34, width: 32, marginRight: 8, marginTop: 8}}
                      source = {{ uri: 'asset:/text.png' }}
                    />
                    <Text style={{ fontSize: 18, marginRight: 5}}>Copy</Text>
                  </TouchableOpacity>
                  {/* -------------------------------------- */}
                  <TouchableOpacity style={styles.cpdc} onPress={()=> paste_method(param1.chooseItems, param1.cfolderId, navigation)}>
                      <Image
                      style={{  height: 24, width: 22, marginRight: 20, marginTop: 8}}
                      source = {{ uri: 'asset:/past.png' }}
                    />
                    <Text style={styles.cpdc_text}>Paste</Text>
                  </TouchableOpacity>
                  {/* -------------------------------------- */}
                  <TouchableOpacity style={styles.cpdc} onPress={()=> setDelete_model(true)} >
                      <Image
                      style={{  height: 24, width: 22, marginRight: 20, marginTop: 8}}
                      source = {{ uri: 'asset:/delete.png' }}
                    />
                    <Text style={styles.cpdc_text} >Delete</Text>
                  </TouchableOpacity>
                  {/* -------------------------------------- */}
                  <TouchableOpacity style={styles.cpdc} onPress={()=> cancel_method(route.name, navigation)}>
                      <Image
                      style={{  height: 22, width: 20, marginRight: 20, marginTop: 8}}
                      source = {{ uri: 'asset:/cancle.png' }}
                    />
                    <Text style={styles.cpdc_text}>Cancle</Text>
                  </TouchableOpacity>
                </View> 
              </Modal>
              :<View></View>
            }
          </View>
        )
      }else if(route.name === 'FolderInside'){

        return(
          <View style={{ flex: 1 }}>
            <TouchableOpacity onPress={() => onpress_three_dot()}>
                <Image
                  style={{ height: 20, width: 20, marginRight: 20, marginTop: 18}}
                  source = {{ uri: 'asset:/3dot.png' }}
                />
              </TouchableOpacity>
              {/* {model_view === true ?
              alert("hello")
            :<View></View>
            }  */}
          </View>
        )

      }
       
    }


    return (
      <NavigationContainer>
        <Stack.Navigator initialRouteName="Home" screenOptions={({ route, navigation }) => ({
          headerRight: () => HomeScreen(route, navigation) })}
            >
          <Stack.Screen name="Home" component={Home} />
          <Stack.Screen  name="MicrosoftLogin" component={MicrosoftLogin} />
          <Stack.Screen name="OneDriveFiles" component={OneDriveFiles} 
            options={({navigation}) => ({
              headerTitle: (props) => <LogoTitle {...props} />,
              headerLeft: () => (
                <TouchableOpacity onPress={() => navigation.navigate('Home') }>
                <Image
                  style={{ width: 20, height: 20, marginBottom: 10, marginLeft: 20 }}
                  source={{ uri: 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTcVY_PPHBXDlGHlFgOxoB_gf5DXTvWp93_YQ&usqp=CAU' }}
                  
                /></TouchableOpacity>),
              
                headerStatusBarHeight: 20,
                justifyContent: 'center',
                alignItems: 'center',
                width: windowWidth
              })
          }
          />
          <Stack.Screen  name="FolderInside" component={FolderInside} />
          <Stack.Screen  name="ShowFile" component={ShowFile} />
          <Stack.Screen  name="VideoFile" component={VideoFile} />
          {/* <Stack.Screen  name="SearchFiles" component={SearchFiles}/> */}
          <Stack.Screen  name="SearchSingleFile" component={SearchSingleFile}/>
          <Stack.Screen  name="NormalVideoExample" component={NormalVideoExample}/>
        </Stack.Navigator>
      </NavigationContainer>
    );
  
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#F5FCFF',
  },
  headerView: {
    marginLeft : -25,
    marginTop: -12,
  },
  cpdc: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: '10%'
  },
  cpdc_text: {
    fontSize: 18
  },
  welcomeHeader: {
    fontSize: 20
  },
  content: {
    position: "absolute",
    bottom: 0,
    width: '90%',
    height: windowHeight / 4,
    borderRadius: 20,
    justifyContent: "center",
    alignItems: "center",
    borderTopRightRadius: 20,
    backgroundColor: "white"
  },
  deleteModel: {
    width: '100%',
    height: windowHeight / 5,
    borderRadius: 20,
    justifyContent: "flex-start",
    alignItems: "center",
    backgroundColor: "white",
    flexDirection: 'column'
  },
  deleteModelText:{
    alignItems: 'center', justifyContent: 'center', fontSize: 19, paddingTop: '10%'
  },
  instructions: {
    textAlign: 'center',
    color: '#333333',
    marginBottom: 5,
  },
});

export default App;
