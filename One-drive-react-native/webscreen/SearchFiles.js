import React, { Component, useState, useEffect } from 'react';
import { View, Text, FlatList, Image, StyleSheet, Button, SafeAreaView, TouchableOpacity } from 'react-native';
import { ListItem, SearchBar } from 'react-native-elements';
import { Dimensions } from 'react-native';

const windowWidth = Dimensions.get('window').width;
const windowHeight = Dimensions.get('window').height;
const patt1 = /\./g;


const SearchFile = ({route}) => {

  const [alldata, setAlldata] = useState([]);
  const [inputtext, setInputtext] = useState('');

  // const all_file = route.params.value;
  // console.log("=============>", all_file.length)

  useEffect(() => {
    setAlldata(route.params.value);
  }, []);

  searchFilterOption = (text) => {
    setInputtext(text);

    const newData = alldata.filter(item => {
      const itemData = `${item.name.toUpperCase()}`;
      const textData = text.toUpperCase();
      return itemData.indexOf(textData) > -1;
    });

    console.log("------->", text);
    setAlldata(newData);
    if (text.length === 0){
      setAlldata(route.params.value);
    }
    if (text.length !== 0 && newData.length === 0){
      setAlldata([{'name': 'NO ITEM FOUND.'}]);
    }
    

  }

  renderHeader = () => {
    return (
      <SearchBar
        placeholder="Type Here..."
        onChangeText={text => searchFilterOption(text)}
        autoCorrect={false}
        value={inputtext}
      />
    );
  };

  renderSeparator = () => {
    return (
      <View
        style={{
          height: 1,
          width: '86%',
          backgroundColor: '#CED0CE',
          marginLeft: '14%',
        }}
      />
    );
  };

  summa = (item) =>{
    // return (
    //   <View style={styles.testItem}>
    //     <Text style={styles.name}>{`${item.name}`}</Text>
    //   </View>
    // )
    if (item.name.match(patt1) === null) {
      return (
        <TouchableOpacity>
          <View style={styles.item}>
                <View style={styles.imageView} > 
                  <Image
                      source={{ uri: 'asset:/image.png' }}
                      style={styles.folderIcon}
                    />
                </View>
                <View style={styles.textView} >
                  <Text style={styles.eachItem} >{item.name}</Text>
                </View>
          </View>
        </TouchableOpacity>
      )
    }else{
      if (item.name.slice(-3) === 'pdf'){
        return (
          <TouchableOpacity>
            <View style={styles.item}>
                  <View style={styles.imageView} > 
                    <Image
                      source={{ uri: 'asset:/pdf.png' }}
                      style={styles.pdfIcon}
                    />
                  </View>
                  <View style={styles.textView} >
                    <Text style={styles.eachItem} >{item.name}</Text>
                  </View>
            </View>
          </TouchableOpacity>
        )

      }else if (item.name.slice(-3) === 'jpg' || item.name.slice(-3) === 'peg' || item.name.slice(-3) === 'png' ){
        return (
          <TouchableOpacity>
            <View style={styles.item}>
                  <View style={styles.imageView} > 
                  <Image
                    source = {{ uri:item['@microsoft.graph.downloadUrl'] }}
                    style={styles.imageIcon}
                  />
                  </View>
                  <View style={styles.textView} >
                    <Text style={styles.eachItem} >{item.name}</Text>
                  </View>
            </View>
          </TouchableOpacity>
        )

      }else if (item.name.slice(-3) === 'mp4'){
        return (
          <TouchableOpacity>
            <View style={styles.item}>
                  <View style={styles.imageView} > 
                  <Image
                      source = {{ uri: 'asset:/video.png' }}
                      style={styles.videoIcon}
                    />
                  </View>
                  <View style={styles.textView} >
                    <Text style={styles.eachItem} >{item.name}</Text>
                  </View>
            </View>
          </TouchableOpacity>
        )

      }else if (item.name.slice(-3) === 'txt'){
        return (
          <TouchableOpacity>
            <View style={styles.item}>
                  <View style={styles.imageView} > 
                  <Image
                      source = {{ uri: 'asset:/text_icon.png' }}
                      style={styles.textIcon}
                    />
                  </View>
                  <View style={styles.textView} >
                    <Text style={styles.eachItem} >{item.name}</Text>
                  </View>
            </View>
          </TouchableOpacity>
        )

      }else{
        return (
          <TouchableOpacity>
            <View style={styles.item}>
                  <View style={styles.imageView} > 
                  <Image
                    source = {{ uri: 'asset:/unknown.png' }}
                    style={{ width: 40, height: 40, margin: 5, borderRadius: 10,
                    }}
                  />
                  </View>
                  <View style={styles.textView} >
                    <Text style={styles.eachItem} >{item.name}</Text>
                  </View>
            </View>
          </TouchableOpacity>
        )

      }

    }
  }



  dataListView = () =>{
    return(
      <View style={{ flex: 1 }}>
        <FlatList
          data={alldata}
          renderItem={({ item }) => summa(item)}
          keyExtractor={item => item.uid}
          // ItemSeparatorComponent={renderSeparator()}
          ListHeaderComponent={renderHeader()}
        />
      </View>
    )
  }

  return (
    <SafeAreaView style={{ flex: 1, alignContent: 'center', justifyContent: 'center'}}>
      {alldata.length === 0 ? <View><Text>Empty</Text></View>: dataListView()}
    </SafeAreaView>
  );
};

export default SearchFile;

const styles = StyleSheet.create({
  testItem: {
    backgroundColor: '#f9c2ff',
    padding: 20,
    marginVertical: 8,
    marginHorizontal: 8,
  },
  name: {
    fontSize: 32,
  },
  container: {
    flex: 1,
  },
  item_st: {
    height: 100,
    // backgroundColor: '#FFC0CB',
    // alignItems: 'center',
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
    width: 40, height: 40, margin: 5
  },
  pdfIcon:{
    width: 40, height: 50, margin: 5
  },
  textIcon:{
    width: 40, height: 40, margin: 5
  },
  videoIcon:{
    width: 40, height: 30, margin: 10
  },
  imageIcon:{
    width: 50, height: 50, margin: 5, borderRadius: 10, borderWidth: 0.5, borderColor: "black"
  },
  item: {
    backgroundColor: '#FFFFFF',
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
    backgroundColor: '#E5E4E2',
    width: '95%',
    marginLeft: 8,
    height: 40,
    borderRadius: 10
  },
  searchText:{
    opacity: 0.3,
    fontSize: 20,
  },
  searchIcon: {
    width: 25, height: 20, marginTop: 10
  },
});