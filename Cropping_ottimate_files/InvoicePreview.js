import React, { Component } from 'react';
import {
  Image, Text, TouchableOpacity, View
} from 'react-native';
import styles from './styles';
import store from '../../../store';
import { connect } from 'react-redux';
import { deleteInvoiceImage } from '../../../actions';
import CloseIcon from 'react-native-vector-icons/Fontisto';
import LeftArrow from 'react-native-vector-icons/Entypo';
import RightArrow from 'react-native-vector-icons/Entypo';
import Colors from '../../../styles/Colors';

class InvoicePreview extends Component {

  constructor(props) {
    super(props);
    const { uploadImagePdf } = store.getState()
    this.state ={
      currentIndex : 0,
      listImages: [...uploadImagePdf.ListDataImages] 
    }
  }

  closeOption = (index) => {
    const { closeButton } = this.props;
    const { uploadImagePdf } = store.getState()

    this.props.deleteInvoiceImage(index)
    this.setState({ currentIndex : 0, listImages: [...uploadImagePdf.ListDataImages]})
    closeButton()
  }

  nextIcon = () => {
    const { currentIndex, listImages } = this.state;
    const { nextImage } = this.props;

    if(currentIndex < listImages.length -1){ 
      this.setState({ currentIndex : currentIndex + 1})
      nextImage(currentIndex + 1)
    }
    
  }

  previousIcon = () => {
    const { currentIndex } = this.state;
    const { previousImage } = this.props;
    
    if(currentIndex > 0){
      this.setState({ currentIndex : currentIndex - 1 })
      previousImage(currentIndex)
    }
  }

  render(){

    const { discard, upload } = this.props;
    const { currentIndex, listImages } = this.state;

    return(

      <View
        contentContainerStyle={styles.containerStyle}
        style={styles.container}
      >

        <View style={styles.imageContainer}>
          <View style={styles.imageBlock}>
            <Image
              source={{ uri: listImages[currentIndex] }}
              style={styles.image}
              resizeMode="contain"
            />
            {listImages.length > 1 ? 
              <>
                <TouchableOpacity style={styles.closeButton} onPress={()=> this.closeOption(currentIndex)}>
                  <CloseIcon name="close-a" size={15} color="#fff" />
                </TouchableOpacity>
                {listImages.length === currentIndex + 1 ? <View></View> :
                  <TouchableOpacity style={styles.rightArrow} onPress={()=> this.nextIcon()}>
                    <LeftArrow name="chevron-right" size={40} color="#fff" />
                  </TouchableOpacity>
                }
                { 1 === currentIndex + 1 ? <View></View> :
                  <TouchableOpacity style={styles.leftArrow} onPress={()=> this.previousIcon()}>
                    <RightArrow name="chevron-left" size={40} color="#fff" />
                  </TouchableOpacity>
                }
              </>
            : null}
          </View>
        </View>
        <View style={styles.bottomContainer}>
          <View style={styles.footerButtons}>
            <TouchableOpacity onPress={() => upload()} style={[styles.bottomButtons, {backgroundColor: Colors.primary}]}>
              <Text style={styles.buttonText}>Upload</Text>
            </TouchableOpacity>
          </View>
          <View style={styles.footerButtons}>
            <TouchableOpacity onPress={() => discard()} style={[styles.bottomButtons, {backgroundColor: Colors.white}]}>
              <Text style={styles.buttonTextDanger}>Discard</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    )
  }
  }

const mapStateToProps = () => ({
});
  
export default connect(
  mapStateToProps,
  { deleteInvoiceImage }
)(InvoicePreview);


---------------------------------------------------------------

import Colors from '../../../styles/Colors';
import { Dimensions } from 'react-native';

export default {
  container: {
    backgroundColor: 'white',
    paddingBottom: 20,
    backgroundColor: Colors.black,
  },
  containerStyle: {
    flex: 1,
    justifyContent: 'space-between',
    flexDirection: 'column',
  },
  imageContainer: {
    height: "83%",
    width: "100%",
    marginTop: "5%",
    // borderWidth: 2,
    // borderColor: Colors.red,
    // borderWidth: 2,
    // borderColor: Colors.white, 
    backgroundColor: Colors.black,
  },
  headerHeight: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    height: "15%",
    width: "100%",
    // backgroundColor: "#FBD6D6"
  },
  subHeaderText:{
      height: "100%",
      justifyContent: 'center',
      alignItems: 'center',
      width: "25%",
      // backgroundColor: "#BED4E3"
  },
  subHeaderIcon:{
    height: "100%",
    width: "25%",
    justifyContent: 'center',
    alignItems: 'center',
    // backgroundColor: "#E1E3BE"
  },
  iconBackGround: {
    backgroundColor: "#E0BEE3",
    height: "70%",
    width: "70"
  },
  imageBlock:{
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: Colors.black,
    height: "100%",
    width: "100%"
  },
  up: {
    height: 22,
    width: 22,
    marginRight: 20,
  },
  bottomContainer: {
    height: "15%",
    width: "100%",
    flexDirection: 'row',
    justifyContent: 'flex-start',
    alignItems: 'flex-start',
    // paddingBottom: 40,
    backgroundColor: Colors.black 
  },
  footerButtons:{
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'flex-start',
    height : '100%', 
    width: '50%'
  },
  bottomButtons:{
    justifyContent: 'center', 
    alignItems: 'center', 
    borderWidth: 1, 
    borderColor: '#777578', 
    height: '70%', 
    width: '90%',
    borderRadius: 5
  },
  image: {
    width: Dimensions.get('window').width -30, // Adjust image width based on your preference
    height: 450, // Adjust image height based on your preference
    // borderWidth: 2,
    // borderColor: Colors.white, 
    // marginRight: 10,
    // marginTop: 10,
    // backgroundColor: '#fff',
    // marginLeft: 8,
    // marginRight: '2%',
  },
  closeButton: {
    position: 'absolute',
    height: 35, 
    width: 35, 
    backgroundColor: "#695C5C",
    borderRadius: 20, 
    justifyContent: "center", 
    alignItems: "center",
    zIndex: 1,
    top: "3%",
    left: "85%"
  },
  rightArrow:{
    position: 'absolute',
    height: 45, 
    width: 45, 
    backgroundColor: '#474343',
    borderRadius: 20, 
    justifyContent: "center", 
    alignItems: "center",
    zIndex: 1,
    top: "40%",
    left: "88%"
  },
  leftArrow:{
    position: 'absolute',
    height: 45, 
    width: 45, 
    backgroundColor: '#474343',
    borderRadius: 20, 
    justifyContent: "center", 
    alignItems: "center",
    zIndex: 1,
    top: "40%",
    right: "88%"
  },
  buttonText: {
    fontSize: 17,
    color: Colors.white
  },
  buttonTextDanger: {
    fontSize: 17,
    color: Colors.red
  }
};

