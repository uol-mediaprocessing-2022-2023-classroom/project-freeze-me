<template>
  <v-app>
    <v-main>
      <!-- Communication between child and parent components can be done using props and events. Props are attributes passed from a parent to a child and can be used within it.
      A child component can emit events, which the parent then may react to. Here "selectedImage" is a prop passed to HomePage. HomePage emits the "fetchImgs" event,
      which triggers the fetchImgs method in App.vue. In this demo this is technically not needed, but since it's a core element of Vue I decided to include it.-->
      <HomePage
        :selectedMedium="selectedMedium"
        :currGallery="currGallery"
        @loadImages="loadImages"
        @updateSelected="updateSelected"
        @getBlur="getBlur"
        @resetGalery="resetGallery"
      />
    </v-main>
  </v-app>
</template>

<script>
import HomePage from "./components/HomePage";
import placeholder from "./assets/placeholder.jpg";

export default {
  name: "App",

  components: {
    HomePage,
  },

  data() {
    return {
      selectedMedium: { url: placeholder, id: "placeholder" },
      currGallery: [],
    };
  },

  methods: {
    /*
    Fetch the first 80 images of a CEWE myPhotos user with a given cldId in a 300 pixel resolution.
    Fetched images are saved within currGallery as data objects, which include the image ID, name, average color, timestamp, data type and the image url.

    @param cldId The client ID of a CEWE myPhotos user, whose photos should be fetched.
    */
    async loadImages(cldId) {
      // First fetch the ids of all the images on a users account, we need these in order to acquire the actual images in a given resolution
      this.allMediaData = await fetch(
        "https://tcmp.photoprintit.com/api/photos/all?orderDirection=asc&showHidden=false&showShared=false&includeMetadata=false",
        { headers: { cldId: cldId, clientVersion: "0.0.0-uni_webapp_demo" } }
      ).then((idResponse) => idResponse.json());

      this.limit = 80;
      this.loadedAmount = 0;
      this.currGallery = [];

      console.log(this.allMediaData)

      // Fetch the actual image urls and other image info using image IDs saved in allImgData
      for (const medium of this.allMediaData.photos) {
        // Stop once the limit is reached
        if (this.loadedAmount >= this.limit) {
          break;
        }
        this.loadedAmount += 1;

        const data = {};
        data.id = medium.id;
        data.name = medium.name;
        data.avgColor = medium.avgHexColor;
        data.timestamp = medium.timestamp;
        data.mimeType = medium.mimeType;

        const mediumResponse = await fetch(
          "https://tcmp.photoprintit.com/api/photos/" +
            medium.id +
            ".jpg?size=300&errorImage=false&cldId=" +
            cldId +
            "&clientVersion=0.0.0-uni_webapp_demo"
        );
        data.url = mediumResponse.url;
        this.currGallery.push(data);
      }
    },

    /*
    Update the selected image visible on the HomePage.

    @param slectedId ID of the selected image.
    */
    async updateSelected(selectedId, cldId) {
      // Fetch the url to the image selected by the user in it's original resolution
      const imgResponse = await fetch(
        "https://tcmp.photoprintit.com/api/photos/" +
          selectedId +
          ".org?size=original&errorImage=false&cldId=" +
          cldId +
          "&clientVersion=0.0.0-uni_webapp_demo"
      );
      const medium = this.currGallery.filter((obj) => {
        return obj.id === selectedId;
      })[0];
      this.selectedMedium = {
        url: imgResponse.url,
        id: selectedId,
        name: medium.name,
        avgColor: medium.avgColor,
        mimeType: medium.mimeType,
      };
    },

    /*
    Display a blurred version of the image.
    The image is processed by the backend and sent to the app.

    @param selectedId ID of the image to be blurred.
    */
    async getBlur(selectedId, cldId) {
      let localUrl = "http://127.0.0.1:8000/get-blur";
      let url = localUrl + "/" + cldId + "/" + selectedId;

      let blurImg = await fetch(url, {
        method: "get",
      })
        .then((response) => response.blob())
        .then((imageBlob) => {
          return URL.createObjectURL(imageBlob);
        });
      console.log(blurImg);
      this.selectedMedium.url = blurImg;
    },

    // Resets cached images.
    resetGallery() {
      this.selectedMedium = { url: placeholder, id: "placeholder" };
      this.currGallery = [];
    },
  },
};
</script>
