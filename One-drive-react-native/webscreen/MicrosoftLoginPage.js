import 'react-native-gesture-handler';
import React, {Component } from 'react';
import { Platform, StyleSheet, Image, Text, View, Button, DeviceEventEmitter } from 'react-native';
import { WebView } from 'react-native-webview';


const url_load = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id=98266b6f-6e0a-44f5-bef8-e8a8b448808e&scope=files.readwrite.all&response_type=token&redirect_uri=https://www.microsoft.com/en-in/microsoft-365/onedrive/online-cloud-storage&client_secret=e3de9ff6-cf86-4cd4-8222-6384b0cbfcaa"

const fetch_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token?client_id=98266b6f-6e0a-44f5-bef8-e8a8b448808e&redirect_uri=https://www.microsoft.com/en-in/microsoft-365/onedrive/online-cloud-storage&client_secret=e3de9ff6-cf86-4cd4-8222-6384b0cbfcaa&code=M.R3_BAY.365e61c7-ab24-edd7-d89d-e13c09bb062c&grant_type=authorization_code"


export default class App extends Component<Props> {

  constructor()  {  
    super();  
    this.state = {  
      isPasswordVisible: true,
      text_access : true,
      access_token: '',
      onedrive_all_files: {},
      loading : false
    }  
  }  


  before_login() {
    return <WebView source = {{ uri: url_load }}
            onNavigationStateChange={this._onNavigationStateChange.bind(this)} />
  }

  after_login(){
    return (
      <View style={styles.container}>
        <Text>Alredy Login .......</Text>
      </View>
    );
  }

  _onNavigationStateChange(webViewState){
    var local_value = '' ;
    var patt1 = /access_token=(\S+)token_type/g; 

    local_value = webViewState.url;

    if (local_value.match(patt1)){
      var token_result = local_value.match(patt1).toString().replace("access_token=", "").replace("token_type", "");;
      console.log(local_value);
      this.setState({ access_token: token_result });
      // console.log(this.state.access_token);
    }else{
      console.log("======== emprt access-token =======");
    }

    
    if (this.state.access_token){

      this.one_drive_files();
      
    }

  };

  
  async one_drive_files(){

    var _urlFiles = "https://graph.microsoft.com/v1.0/me/drive/root/children";


    let response_data = await fetch(_urlFiles, {
  
          method: 'GET',
          headers: new Headers({
              'Authorization': 'Bearer '+ this.state.access_token, 
              'Accept': 'application/json'
            }),
          }).then(
          ).catch(function(err) {
          console.log('Fetch Error :-S', err);
        });
    
    let files_list = await response_data.json();
    
    this.setState({ onedrive_all_files : files_list });
    
    console.log("------------>", this.state.onedrive_all_files);
    this.state.onedrive_all_files.chooseItems = [];
    this.state.onedrive_all_files.cfolderId = [];
    this.state.onedrive_all_files.folderNavigation = [];

    if (this.state.onedrive_all_files){
      this.setState({ loading : true });
      this.state.onedrive_all_files.value.accessToken = this.state.access_token;
      this.props.navigation.navigate('OneDriveFiles', this.state.onedrive_all_files);
    }
      
    return files_list;
  };


  render() {
    return <View style = {styles.container} >
              {this.state.isPasswordVisible ? this.before_login() : this.after_login()}
            </View>;
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  container_2: {
    flex: 1,
  },
  welcome: {
    fontSize: 20,
    textAlign: 'center',
    margin: 10,
  },
  instructions: {
    textAlign: 'center',
    color: '#333333',
    marginBottom: 5,
  },
});