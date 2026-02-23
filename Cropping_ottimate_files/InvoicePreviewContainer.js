import React, { Component } from 'react';
import { TouchableOpacity, Text } from 'react-native';
import { connect } from 'react-redux';
import { addPendingUpload, deleteAllInvoiceImage } from '../../../actions';
import InvoicePreview from '../../../components/Upload/InvoicePreview';
import store from '../../../store';
import { deleteFile } from '../../../utils/FileUtil';
import PlusIcon from 'react-native-vector-icons/MaterialIcons';
import { MixpanelEvents, sendMixpanelEvent } from '../../../utils/mixpanel/MixPanelAdapter';
import { View } from 'react-native';


class InvoicePreviewContainer extends Component {

  constructor(props) {
    super(props);
    const { restaurant } = this.props.navigation.state.params;
    this.state = {
      restaurant
    }
  }

  static navigationOptions = ({ navigation }) => {
    const currentIndex = navigation.getParam('currentIndex', 0);
    const totalImages = navigation.getParam('totalImages', 1)
  
    return {
      headerTitle: () => (
        <View style={{ flexDirection: 'row', alignItems: 'center', marginRight: '80%' }}>
          <TouchableOpacity onPress={() => null}>
            <Text style={{ fontSize: 18 }}>{currentIndex + 1}/ {totalImages}</Text>
          </TouchableOpacity>
        </View>
      ),
      headerRight: () =>(
        <View style={{height: 50, width: 50, justifyContent: 'center', alignItems: 'center', marginRight: 15}}>
          <TouchableOpacity onPress={()=> navigation.goBack()} style={{ height: '70%', width: '70%', alignItems: 'center', justifyContent: 'center'}}>
            <PlusIcon name="add-a-photo" size={35} />
          </TouchableOpacity>
        </View>
      ),
    };
  };

  componentDidMount(){
    const { uploadImagePdf } = store.getState();
    this.props.navigation.setParams({ totalImages: uploadImagePdf.ListDataImages.length })
    this.props.navigation.setParams({ currentIndex: 0 })
  }

  nextImage = (imgIndex) => {
    this.props.navigation.setParams({ currentIndex: imgIndex });
  }

  previousImage = (imgIndex) => {
    imgIndex = imgIndex - 1 
    this.props.navigation.setParams({ currentIndex: imgIndex });
  }


  addImageIcon = () => {
    this.props.navigation.goBack();
  }

  closeButton = () => {
    const { uploadImagePdf } = store.getState();
    this.props.navigation.setParams({ currentIndex: 0 })
    this.props.navigation.setParams({ totalImages: uploadImagePdf.ListDataImages.length })
  }

  discard = async () => {
    const { uploadImagePdf } = store.getState();
    for (let eachImg of uploadImagePdf.ListDataImages) {
      await deleteFile(eachImg);
    }
    this.props.deleteAllInvoiceImage();
    this.props.navigation.goBack();
  };

  upload = () => {
    const { uploadImagePdf } = store.getState();

    sendMixpanelEvent(MixpanelEvents.INVOICE_UPLOADED);
    const { restaurant } = this.props.navigation.state.params;
    for (let eachImage of uploadImagePdf.ListDataImages){
      this.props.addPendingUpload(restaurant, eachImage, null, {});
    }
    this.props.deleteAllInvoiceImage();
    this.props.navigation.navigate('UploadInvoice');
  }

  render() {
    const { restaurant } = this.props.navigation.state.params;
    const nextImage = this.nextImage.bind(this);
    const previousImage = this.previousImage.bind(this);
    const closeButton = this.closeButton.bind(this);
    
    return (
      <InvoicePreview
        restaurant={restaurant}
        discard={this.discard}
        nextImage={nextImage}
        previousImage={previousImage}
        closeButton={closeButton}
        upload={this.upload}
      />
    );
  }
}

const mapStateToProps = () => ({
});

export default connect(
  mapStateToProps,
  { addPendingUpload, deleteAllInvoiceImage }
)(InvoicePreviewContainer);

