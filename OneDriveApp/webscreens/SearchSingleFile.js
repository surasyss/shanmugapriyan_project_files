import React, { Component, useState, useEffect } from 'react';
import { View, Text, FlatList, Image, StyleSheet, Button, SafeAreaView, TouchableOpacity } from 'react-native';
import { Input, SearchBar } from 'react-native-elements';
import { Dimensions, TextInput } from 'react-native';
import { color } from 'react-native-elements/dist/helpers';
import Loader from './Loder.js';

const windowWidth = Dimensions.get('window').width;
const windowHeight = Dimensions.get('window').height;

var patt1 = /\./g;

class SearchSingleFile extends Component {

    constructor()  {
        super();  

        this.state = {  
          inputText: '',
          fileDisplay : false,
          loading: false,
          resultFille : [],
        }

    }
    componentDidMount() {

        console.log("---------->", this.props.route.params.access);
    }

    async access_search_file(){


        var _urlFiles = `https://graph.microsoft.com/v1.0//me/drive/root/search(q='{${this.state.inputText}}')`;
        

        let response_data = await fetch(_urlFiles, {
    
            method: 'GET',
            headers: new Headers({
                'Authorization': 'Bearer '+ this.props.route.params.access,
                'Accept': 'application/json'
                }),
            }).then(
            ).catch(function(err) {
              this.setState({ loading : false });
            console.log('Fetch Error :-S', err);
            });
          
        let each_folder_list = await response_data.json();


        if (each_folder_list.value.length > 0){
            this.setState({ loading : false });
            this.setState({ fileDisplay : true });
            this.setState({ resultFille :  each_folder_list.value });
            console.log("------------------>", this.state.resultFille[0].name)
        }else{
            this.setState({ loading : false });
            alert('file not funded');
        }
        
        
      
    }

    updateSearch = (inputText) => {
        this.setState({ inputText });

        if (inputText.length > 2) {
 
            console.log("======== updateSearch", this.state.inputText)
            setTimeout(() => {
            console.log("====== setTimeout")
            this.setState({ loading : true });
            this.access_search_file();
            // setTimeout(() =>{ this.setState({ loading : false })}, 9000)
            }, 8000);
            
        }else{
            // this.state.resultFille = [];
        }
    
        
    };

    cancel_click = () =>{ console.log(" - --- cancel -------"), this.setState({ fileDisplay : false})}


    fileView(){
        if (this.state.resultFille.length !==0){
            return this.inner_view_files();
        }
    }

    inner_view_files(){
        if (this.state.resultFille[0].name.match(patt1) === null) {
            return(
                <TouchableOpacity>
                    <View style={styles.item}>
                        <View style={styles.imageView} >
                        <Image
                            source = {{ uri: 'asset:/folder.png' }}
                            style={{ width: 40, height: 40, margin: 5, borderRadius: 10,
                            }}
                        />
                        </View>
                        <View style={styles.textView} >
                            {this.state.resultFille.length !==0 ?<Text style={styles.eachItem} >{this.state.resultFille[0].name}</Text> : <Text>name</Text> }
                        </View>
                    </View>
                </TouchableOpacity>
            )

        }else{
            return(
                <TouchableOpacity>
                    <View style={styles.item}>
                        <View style={styles.imageView} >
                        <Image
                            source = {{ uri: 'asset:/image.png' }}
                            style={{ width: 40, height: 40, margin: 5, borderRadius: 10,
                            }}
                        />
                        </View>
                        <View style={styles.textView} >
                            {this.state.resultFille.length !==0 ?<Text style={styles.eachItem} >{this.state.resultFille[0].name}</Text> : <Text>name</Text> }
                        </View>
                    </View>
                </TouchableOpacity>
            )

        }
    }

    // buttonDisplay(accessKey){
    //     return(
    //         <View style={styles.container} >
    //             <TouchableOpacity style={styles.submitBotton} onPress={() => this.access_search_file(accessKey) }>
    //                 <Text style={styles.buttonText} >submit</Text></TouchableOpacity>
    //         </View>
    //     )
    // }

    // search_the_file = () =>{

    //     if (this.state.inputText.length > 2) {
         
    //         setTimeout(() => {
    //             alert(this.state.inputText);
    //         }, 1000);
    
    //     }else{
    //         alert('No item funded')
    //     }
    // }

    

    render() {

        const accessKey = this.props.route.params.access;

        return (
                <View style={{ height: 56}} >
                    <Loader loading={this.state.loading} />
                    <SearchBar
                        placeholder="Type Here..."
                        onChangeText={this.updateSearch}
                        lightTheme={true}
                        searchIcon={{ color: '#808080'}}
                        placeholderTextColor="#808080"
                        inputContainerStyle={{  backgroundColor: 'white' }}
                        onClear={this.cancel_click}
                        value={this.state.inputText}
                    />
                    {this.state.fileDisplay ? this.fileView() : <View></View>}
                </View>
            );
    }

}

export default SearchSingleFile;

const styles = StyleSheet.create({
    container: {
        flex:1,
        backgroundColor: '#D5D6EA',
        flexDirection:'row',
        alignItems:'center',
        justifyContent:'center'
    },
    searchOption:{
        flex: 1,
        flexDirection: 'row',
        height: 45,
        // width: '96%',
        // marginLeft: '2%',
        borderRadius: 25,
        backgroundColor: '#D3D3D3',
        // borderWidth: 0.5
    },
    searchIcon: {
        width: '8%', height: '47%', marginTop: '4.5%', marginLeft: '4%'
      },
    searchDiv: {
        height: '8%',
        backgroundColor: '#808080',
        width: '10%'
    },
    buttonText: {
        margin: 15
    },
    item: {
        backgroundColor: '#AFC8E7',
        // padding: -5,
        height: 100,
        marginVertical: 1,
        marginHorizontal: 1,
      },
    imageView:{
        marginTop: 20,
        marginLeft: 10,
        width: 60, 
        height: 60,
        // backgroundColor : '#800000',
        alignItems:'center',
    },
    textView: {
        width: windowWidth,
        height: 60,
        // backgroundColor : '#ADD8E6',
        marginTop: -60,
        left : 70,
    },
    eachItem: {
        marginTop: 2,
        marginLeft: 10, 
        fontSize: 18,
    },
  })
  