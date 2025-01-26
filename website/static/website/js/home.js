// JavaScript Document

jQuery(document).ready(function($) {
	$(window).on('load', function() {
	
		"use strict";

						
		/*----------------------------------------------------*/
		/*	Preloader
		/*----------------------------------------------------*/
		
		var preloader = $('#loader-wrapper'),
			loader = preloader.find('.cssload-loader');
			loader.fadeOut();
			preloader.delay(400).fadeOut('slow');
				
	});


	$(window).on('scroll', function() {
		
		"use strict";

								
		/*----------------------------------------------------*/
		/*	Navigtion Menu Scroll
		/*----------------------------------------------------*/	
		
		var b = $(window).scrollTop();
		
		if( b > 80 ){		
			$(".wsmainfull").addClass("scroll");
		} else {
			$(".wsmainfull").removeClass("scroll");
		}				

	});


	$(document).ready(function() {
			
		"use strict";


		/*----------------------------------------------------*/
		/*	Hero Slider
		/*----------------------------------------------------*/

		$('.slider').slider({
			full_width: false,
			interval:6000,
			transition:1000,
			draggable: false,
			indicators: true,
		});

		$('.slide-next').click(function() {
			$('.slider').slider('next');
		});

		$('.slide-prev').click(function() {
			$('.slider').slider('prev');
		});


		/*----------------------------------------------------*/
		/*	Hero Text Rotator
		/*----------------------------------------------------*/
	
		$('.hero-txt-rotator').flexslider({
			animation: "fade",
			controlNav: true,
			directionNav: false,  
			slideshowSpeed: 6000,   
			animationSpeed: 700,  
			start: function(slider){
				$('body').removeClass('loading');
			}
		});


		/*----------------------------------------------------*/
		/*	Animated Scroll To Anchor
		/*----------------------------------------------------*/
		
		$('.header a[href^="#"], .wsmenu a[href^="#"], .page a.btn[href^="#"], .page a.internal-link[href^="#"]').on('click', function (e) {
			
			e.preventDefault();

			var target = this.hash,
				$target = jQuery(target);

			$('html, body').stop().animate({
				'scrollTop': $target.offset().top - 60 // - 200px (nav-height)
			}, 'slow', 'easeInSine', function () {
				window.location.hash = '1' + target;
			});
			
		});


		/*----------------------------------------------------*/
		/*	Accordion
		/*----------------------------------------------------*/

		$(".accordion > .accordion-item.is-active").children(".accordion-panel").slideDown();
				
		$(".accordion > .accordion-item").click(function() {
			$(this).siblings(".accordion-item").removeClass("is-active").children(".accordion-panel").slideUp();
			$(this).toggleClass("is-active").children(".accordion-panel").slideToggle("ease-out");
		});

		
		/*----------------------------------------------------*/
		/*	Single Image Lightbox
		/*----------------------------------------------------*/
				
		$('.image-link').magnificPopup({
		  type: 'image'
		});	


		/*----------------------------------------------------*/
		/*	Video Link #1 Lightbox
		/*----------------------------------------------------*/
		
		$('.video-popup1').magnificPopup({
		    type: 'iframe',		  	  
				iframe: {
					patterns: {
						youtube: {			   
							index: 'youtube.com',
							src: 'https://www.youtube.com/embed/SZEflIVnhH8'				
								}
							}
						}		  		  
		});


		/*----------------------------------------------------*/
		/*	Video Link #2 Lightbox
		/*----------------------------------------------------*/
		
		$('.video-popup2').magnificPopup({
		    type: 'iframe',		  	  
				iframe: {
					patterns: {
						youtube: {			   
							index: 'youtube.com',
							src: 'https://www.youtube.com/embed/7e90gBu4pas'				
								}
							}
						}		  		  
		});


		/*----------------------------------------------------*/
		/*	Video Link #3 Lightbox
		/*----------------------------------------------------*/
		
		$('.video-popup3').magnificPopup({
		    type: 'iframe',		  	  
				iframe: {
					patterns: {
						youtube: {			   
							index: 'youtube.com',
							src: 'https://www.youtube.com/embed/0gv7OC9L2s8'					
								}
							}
						}		  		  
		});


		/*----------------------------------------------------*/
		/*	Statistic Counter
		/*----------------------------------------------------*/
	
		$('.count-element').each(function () {
			$(this).appear(function() {
				$(this).prop('Counter',0).animate({
					Counter: $(this).text()
				}, {
					duration: 4000,
					easing: 'swing',
					step: function (now) {
						$(this).text(Math.ceil(now));
					}
				});
			},{accX: 0, accY: 0});
		});


		/*----------------------------------------------------*/
		/*	Gallery Photo Rotator
		/*----------------------------------------------------*/
	
		var owl = $('.gallery-photo');
			owl.owlCarousel({
				items: 4,
				loop:true,
				autoplay:true,
				navBy: 1,
				autoplayTimeout: 4500,
				autoplayHoverPause: false,
				smartSpeed: 3000,
				responsive:{
					0:{
						items:1
					},
					640:{
						items:1
					},
					767:{
						items:2
					},
					768:{
						items:2
					},
					991:{
						items:3
					},				
					1000:{
						items:4
					}
				}
		});


		/*----------------------------------------------------*/
		/*	Testimonials Rotator
		/*----------------------------------------------------*/
	
		var owl = $('.reviews-wrapper');
			owl.owlCarousel({
				items: 3,
				loop:true,
				autoplay:true,
				navBy: 1,
				autoplayTimeout: 4500,
				autoplayHoverPause: true,
				smartSpeed: 1500,
				responsive:{
					0:{
						items:1
					},
					767:{
						items:1
					},
					768:{
						items:2
					},
					991:{
						items:3
					},
					1000:{
						items:3
					}
				}
		});


		/*----------------------------------------------------*/
		/*	Brands Logo Rotator
		/*----------------------------------------------------*/
	
		var owl = $('.brands-carousel');
			owl.owlCarousel({
				items: 5,
				loop:true,
				autoplay:true,
				navBy: 1,
				nav:false,
				autoplayTimeout: 4000,
				autoplayHoverPause: false,
				smartSpeed: 2000,
				responsive:{
					0:{
						items:2
					},
					550:{
						items:3
					},
					767:{
						items:3
					},
					768:{
						items:4
					},
					991:{
						items:5
					},				
					1000:{
						items:6
					}
				}
		});


		/*----------------------------------------------------*/
		/*	Masonry Grid
		/*----------------------------------------------------*/

		$('.grid-loaded').imagesLoaded(function () {

	        // filter items on button click
	        $('.masonry-filter').on('click', 'button', function () {
	            var filterValue = $(this).attr('data-filter');
	            $grid.isotope({
	              filter: filterValue
	            });
	        });

	        // change is-checked class on buttons
	        $('.masonry-filter button').on('click', function () {
	            $('.masonry-filter button').removeClass('is-checked');
	            $(this).addClass('is-checked');
	            var selector = $(this).attr('data-filter');
	            $grid.isotope({
	              filter: selector
	            });
	            return false;
	        });

	        // init Isotope
	        var $grid = $('.masonry-wrap').isotope({
	            itemSelector: '.masonry-item',
	            percentPosition: true,
	            transitionDuration: '0.7s',
	            masonry: {
	              // use outer width of grid-sizer for columnWidth
	              columnWidth: '.masonry-item',
	            }
	        });
	        
	    });


	});

});
